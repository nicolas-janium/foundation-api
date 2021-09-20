import os
from unittest.mock import Mock
from uuid import uuid4

import requests
from bs4 import BeautifulSoup as Soup
from flask import Response

from model import (Janium_campaign, Ulinc_campaign,
                   Ulinc_campaign_origin_message, Ulinc_config,
                   create_gcf_db_engine, create_gcf_db_session)


def extract_campaign_id(url):
    return url.split('/')[-2]

def get_campaign_message(ulinc_client_id, ulinc_campaign_id, usr, pwd, is_messenger=False):
    url = "https://ulinc.co/{}/campaigns/{}".format(ulinc_client_id, ulinc_campaign_id)

    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', usr)
    jar.set('pwd', pwd)

    res = requests.get(url=url, cookies=jar)
    if res.ok:
        soup = Soup(res.text, 'html.parser')
        message_type = "message[welcome]" if is_messenger else "message[connection]"
        if message_item := soup.find('textarea', {"name": message_type}):
            if message_text := message_item.get_text():
                return message_text
            else:
                return None
        else:
            return None
    return None

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
                    "is_active": True if td_list[1].find('span').text == 'Active' else False,
                    "origin_message": get_campaign_message(ulinc_config.ulinc_client_id, str(extract_campaign_id(td_list[0].find('a')['href'])), usr, pwd, is_messenger=False)
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
                    "is_active": True if td_list[1].find('span').text == 'Active' else False,
                    "origin_message": get_campaign_message(ulinc_config.ulinc_client_id, str(extract_campaign_id(td_list[0].find('a')['href'])), usr, pwd, is_messenger=True)
                }
                campaigns['messenger'].append(camp_dict)
        return campaigns
    return None

def insert_campaigns(ulinc_config_id, ulinc_campaign_dict, session):
    for ulinc_campaign in ulinc_campaign_dict['connector']:
        if existing_ulinc_campaign := session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_config_id == ulinc_config_id).filter(Ulinc_campaign.ulinc_ulinc_campaign_id == ulinc_campaign['ulinc_campaign_id']).first():
            existing_ulinc_campaign.ulinc_campaign_name = ulinc_campaign['name']
            existing_ulinc_campaign.ulinc_is_active = ulinc_campaign['is_active']
            ulinc_campaign_id = existing_ulinc_campaign.ulinc_campaign_id
        else:
            ulinc_campaign_id = str(uuid4())
            new_ulinc_campaign = Ulinc_campaign(
                ulinc_campaign_id,
                ulinc_config_id,
                Janium_campaign.unassigned_janium_campaign_id,
                ulinc_campaign['name'],
                ulinc_campaign['is_active'],
                ulinc_campaign['ulinc_campaign_id'],
                False
            )
            session.add(new_ulinc_campaign)
        if ulinc_campaign['origin_message']:
            if existing_origin_message := session.query(Ulinc_campaign_origin_message).filter(Ulinc_campaign_origin_message.message == ulinc_campaign['origin_message']).first():
                pass
            else:
                ulinc_campaign_origin_message = Ulinc_campaign_origin_message(
                    str(uuid4()),
                    ulinc_campaign_id,
                    ulinc_campaign['origin_message'],
                    False
                )
                session.add(ulinc_campaign_origin_message)
        session.commit()

    for ulinc_campaign in ulinc_campaign_dict['messenger']:
        if existing_ulinc_campaign := session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_config_id == ulinc_config_id).filter(Ulinc_campaign.ulinc_ulinc_campaign_id == ulinc_campaign['ulinc_campaign_id']).first():
            existing_ulinc_campaign.ulinc_campaign_name = ulinc_campaign['name']
            existing_ulinc_campaign.ulinc_is_active = ulinc_campaign['is_active']
            ulinc_campaign_id = existing_ulinc_campaign.ulinc_campaign_id
        else:
            ulinc_campaign_id = str(uuid4())
            new_ulinc_campaign = Ulinc_campaign(
                ulinc_campaign_id,
                ulinc_config_id,
                Janium_campaign.unassigned_janium_campaign_id,
                ulinc_campaign['name'],
                ulinc_campaign['is_active'],
                ulinc_campaign['ulinc_campaign_id'],
                True
            )
            session.add(new_ulinc_campaign)
        if ulinc_campaign['origin_message']:
            if existing_origin_message := session.query(Ulinc_campaign_origin_message).filter(Ulinc_campaign_origin_message.message == ulinc_campaign['origin_message']).first():
                pass
            else:
                ulinc_campaign_origin_message = Ulinc_campaign_origin_message(
                    str(uuid4()),
                    ulinc_campaign_id,
                    ulinc_campaign['origin_message'],
                    True
                )
                session.add(ulinc_campaign_origin_message)
        session.commit()
    session.commit()

def refresh_ulinc_campaigns(ulinc_config, session):
    if ulinc_campaign_dict := get_ulinc_campaigns(ulinc_config):
        if ulinc_campaign_dict['connector'] or ulinc_campaign_dict['messenger']:
            insert_campaigns(ulinc_config.ulinc_config_id, ulinc_campaign_dict, session)
            return True
        return True
    return None

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if ulinc_config := session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first():
            if ulinc_config.is_working:
                if refresh_ulinc_campaigns(ulinc_config, session):
                    return Response("Success", 200) # Task should not repeat
                return Response("Try again", 300) # Task should repeat
            return Response("Ulinc_config not working", 200) # Task should not repeat
        return Response("Unknown ulinc_config_id", 200) # Task should not repeat


if __name__ == '__main__':
    data = {"ulinc_config_id": "d0b9f557-942c-4d5f-b986-8ff935ebce81"}
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
