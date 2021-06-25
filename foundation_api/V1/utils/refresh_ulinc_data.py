import base64
import json
from datetime import datetime
from uuid import uuid4
import logging
import os

import requests
from bs4 import BeautifulSoup as Soup
from foundation_api.V1.sa_db.model import *

def get_cookie(username, password):
    login_url = 'https://ulinc.co/login/?email={}&password={}&sign=1'.format(username, password)

    req_session = requests.Session()
    login = req_session.post(url=login_url)

    if login.ok:
        ulinc_cookie = {}
        if login.history:
            for cookie in login.history[0].cookies:
                if cookie.name == 'PHPSESSID':
                    continue
                elif cookie.name == 'usr':
                    ulinc_cookie['usr'] = cookie.value
                    ulinc_cookie['expires'] = datetime.fromtimestamp(cookie.expires).strftime(r'%Y-%m-%d %H:%M:%S')
                elif cookie.name == 'pwd':
                    ulinc_cookie['pwd'] = cookie.value 
            return ulinc_cookie
        else:
            return None
    else:
        return None

def refresh_ulinc_cookie(ulinc_config):
    if ulinc_cookie := get_cookie(ulinc_config.credentials.username, ulinc_config.credentials.password):
        if ulinc_config.cookie_id == Cookie.unassigned_cookie_id:
            new_cookie = Cookie(str(uuid4()), 1, ulinc_cookie)
            db.session.add(new_cookie)
            ulinc_config.cookie_id = new_cookie.cookie_id
            print("Created new ulinc cookie for ulinc config {}".format(ulinc_config.ulinc_config_id))
        else:
            cookie = db.session.query(Cookie).filter(Cookie.cookie_id == ulinc_config.cookie_id).first()
            cookie.cookie_json_value = ulinc_cookie
            print("Updated existing cookie for ulinc config {}".format(ulinc_config.ulinc_config_id))
        ulinc_config.is_working = True
        db.session.commit()
    else:
        print("Error while refreshing ulinc cookie")
        ulinc_config.is_working = False
        db.session.commit()

def extract_campaign_id(url):
    return url.split('/')[-2]

def get_ulinc_campaigns(ulinc_config):
    req_session = requests.Session()
    get_connector_campaigns_url = 'https://ulinc.co/{}/?do=campaigns&act=campaigns'.format(ulinc_config.ulinc_client_id)
    get_messenger_campaigns_url = 'https://ulinc.co/{}/?do=campaigns&act=bulk_campaigns'.format(ulinc_config.ulinc_client_id)

    usr = ulinc_config.cookie.cookie_json_value['usr']
    pwd = ulinc_config.cookie.cookie_json_value['pwd']
    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', usr)
    jar.set('pwd', pwd)

    campaigns = {
        "connector": [],
        "messenger": []
    }

    connector_campaigns_table = req_session.get(url=get_connector_campaigns_url, cookies=jar)
    messenger_campaigns_table = req_session.get(url=get_messenger_campaigns_url, cookies=jar)
    if connector_campaigns_table.ok and messenger_campaigns_table.ok:
        ### Get connector campaigns ###
        c_soup = Soup(connector_campaigns_table.text, 'html.parser')
        c_table_body = c_soup.find('tbody')
        if len(c_table_body.find_all('tr')) > 0:
            for tr in c_table_body.find_all('tr'):
                td_list = tr.find_all('td')
                camp_dict = {
                    "name": td_list[0].text,
                    "ulinc_campaign_id": str(extract_campaign_id(td_list[0].find('a')['href'])),
                    "is_active": True if td_list[1].find('span').text == 'Active' else False
                }
                campaigns['connector'].append(camp_dict)

        ### Get messenger campaigns ###
        m_soup = Soup(messenger_campaigns_table.text, 'html.parser')
        m_table_body = m_soup.find('tbody')
        if len(m_table_body.find_all('tr')) > 0:
            for tr in m_table_body.find_all('tr'):
                td_list = tr.find_all('td')
                ulinc_campaign_id = str(extract_campaign_id(td_list[0].find('a')['href']))
                camp_dict = {
                    "name": td_list[0].text,
                    "ulinc_campaign_id": ulinc_campaign_id,
                    "is_active": True if td_list[1].find('span').text == 'Active' else False
                }
                campaigns['messenger'].append(camp_dict)

        return campaigns
    return None

def insert_campaigns(ulinc_config_id, ulinc_campaign_dict):
    for ulinc_campaign in ulinc_campaign_dict['connector']:
        existing_ulinc_campaign = db.session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_config_id == ulinc_config_id).filter(Ulinc_campaign.ulinc_ulinc_campaign_id == ulinc_campaign['ulinc_campaign_id']).first()
        if existing_ulinc_campaign:
            existing_ulinc_campaign.ulinc_campaign_name = ulinc_campaign['name']
            existing_ulinc_campaign.ulinc_is_active = ulinc_campaign['is_active']
        else:
            new_ulinc_campaign = Ulinc_campaign(
                str(uuid4()),
                ulinc_config_id,
                Janium_campaign.unassigned_janium_campaign_id,
                ulinc_campaign['name'],
                ulinc_campaign['is_active'],
                ulinc_campaign['ulinc_campaign_id'],
                False
            )
            db.session.add(new_ulinc_campaign)

    for ulinc_campaign in ulinc_campaign_dict['messenger']:
        existing_ulinc_campaign = db.session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_config_id == ulinc_config_id).filter(Ulinc_campaign.ulinc_ulinc_campaign_id == ulinc_campaign['ulinc_campaign_id']).first()
        if existing_ulinc_campaign:
            existing_ulinc_campaign.ulinc_campaign_name = ulinc_campaign['name']
            existing_ulinc_campaign.ulinc_is_active = ulinc_campaign['is_active']
        else:
            new_ulinc_campaign = Ulinc_campaign(
                str(uuid4()),
                ulinc_config_id,
                Janium_campaign.unassigned_janium_campaign_id,
                ulinc_campaign['name'],
                ulinc_campaign['is_active'],
                ulinc_campaign['ulinc_campaign_id'],
                True
            )
            db.session.add(new_ulinc_campaign)

    db.session.commit()

def refresh_ulinc_campaigns(ulinc_config):
    if ulinc_config.cookie_id != Cookie.unassigned_cookie_id:
        if ulinc_campaign_dict := get_ulinc_campaigns(ulinc_config):
            if ulinc_campaign_dict['connector'] or ulinc_campaign_dict['messenger']:
                insert_campaigns(ulinc_config.ulinc_config_id, ulinc_campaign_dict)
                return 1
            else:
                print('Campaign dict empty. No campaigns')
                return 1
        else:
            return None
    else:
        print('Ulinc cookie does not exist for ulinc_config {}'.format(ulinc_config.ulinc_config_id))
        return None

def main(account_id, ulinc_config_id, ulinc_client_id, ulinc_config_cookie_id, cookie_json_value, username, password):
    if account := db.session.query(Account).filter(Account.account_id == account_id).first():
        refresh_ulinc_cookie(account_id, ulinc_config_id, ulinc_config_cookie_id, username, password)

        refresh_ulinc_campaigns(account_id, ulinc_config_id, cookie_json_value)

        return 1


if __name__ == '__main__':
    # account_id = "ccddacca-2106-46ea-911a-41c46040e60a"
    # main(account_id)
    print(get_cookie('jhawkes20@gmail.com', 'JA12345!'))
    # print(get_cookie('jhawkes20@gmail.com', 'JA12345!123'))
