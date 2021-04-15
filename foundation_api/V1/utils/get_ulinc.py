from datetime import datetime
import os
from pprint import pprint

import requests
from bs4 import BeautifulSoup as Soup


def get_ulinc_client_id(url):
    for part in str(url).rsplit('/')[::-1]:
        if part:
            return part

def get_ulinc_client_info(username, password, li_email):
    login_url = 'https://ulinc.co/login/?email={}&password={}&sign=1'.format(username, password)

    account_url = 'https://ulinc.co/accounts/'
    session = requests.Session()
    login = session.post(url=login_url)

    if login.ok:
        login_soup = Soup(login.text, 'html.parser')
        if login_soup.find('div', **{'class': 'login-container'}):
            return {
                "ok": True,
                "is_login": False
            }
        elif not login_soup.find('div', **{'class': 'box-body'}).find('table'):
            return {
                "ok": True,
                "is_login": True,
                "has_account": False
            }

    jar = requests.cookies.RequestsCookieJar()
    ulinc_cookie = {}

    for cookie in login.history[0].cookies:
        if cookie.name == 'PHPSESSID':
            continue
        elif cookie.name == 'usr':
            ulinc_cookie['usr'] = cookie.value
            ulinc_cookie['expires'] = datetime.fromtimestamp(cookie.expires).strftime(r'%Y-%m-%d %H:%M:%S')
            jar.set('usr', cookie.value)
        elif cookie.name == 'pwd':
            ulinc_cookie['pwd'] = cookie.value
            jar.set('pwd', cookie.value)

    account_page = session.get(url=account_url, cookies=jar)
    ulinc_account_id = None
    if account_page.ok:
        # print(account_page.text)
        accounts_page_soup = Soup(account_page.text, 'html.parser')
        accounts_table = accounts_page_soup.find('table', **{"class": "table"})
        for tr_tag in accounts_table.find_all('tr'):
            td_item = tr_tag.find_all('td')[0]
            active_td_item = tr_tag.find_all('td')[1]
            ulinc_li_email = td_item.text
            if ulinc_li_email == li_email:
                ulinc_account_link = td_item.find('a')['href']
                ulinc_account_id = get_ulinc_client_id(ulinc_account_link)
                ulinc_is_active = True if active_td_item.text == 'Active' else False
                break
            else:
                continue
        
        if ulinc_account_id:
            sub_url = "https://ulinc.co/subscription/"
            sub_page = session.get(url=sub_url, cookies=jar)
            if sub_page.ok:
                sub_soup = Soup(sub_page.text, 'html.parser')
                current_plan = sub_soup.find('span', **{'class': 'info-box-number'}).text
                if str(current_plan).lower() != 'business':
                    return {
                        "ok": True,
                        "is_login": True,
                        "has_account": True,
                        "is_business": False,
                        "ulincid": ulincid,
                        "user_cookie": ulinc_cookie,
                    }
        else:
            return "There is no Ulinc LinkedIn Email for this Ulinc Account"


    id_index = account_page.text.find('acc_')
    user_id1 = account_page.text[id_index + 4:id_index + 11]

    soup = Soup(account_page.text, 'html.parser')
    for link in soup.find_all('a'):
        if link.text == 'Settings':
            account_settings_link = link['href']
            user_id2 = account_settings_link.split('/')[3]

    if user_id1 == user_id2:
        ulincid = user_id1



    settings_url = 'https://ulinc.co/{}/?do=accounts&act=settings'.format(ulincid)
    settings_page = session.get(url=settings_url, cookies=jar)

    webhooks_activated = []
    webhooks = {}
    if settings_page.ok:
        settings_soup = Soup(settings_page.text, 'html.parser')
        wh_divs = settings_soup.find_all('div', **{'class': 'zap_link'})
        for i, wh_div in enumerate(wh_divs):
            if str(wh_div.find('a').text).lower() == 'deactivate':
                if i == 0:
                    webhooks['new_connection'] = wh_div.find('input').get('value')
                elif i == 1:
                    webhooks['new_message'] = wh_div.find('input').get('value')
                elif i == 2:
                    webhooks['send_message'] = wh_div.find('input').get('value')
            else:
                activate_wh = session.get(url="https://ulinc.co/{}/?do=accounts&act=zap_toggle&id={}".format(ulincid, i + 1))
                if activate_wh.ok:
                    # print("Activated webhook {}".format(i + 1))
                    settings_page = session.get(url=settings_url, cookies=jar)
                    settings_soup = Soup(settings_page.text, 'html.parser')
                    wh_div = settings_soup.find('div', **{'id': 'zap{}'.format(i + 1)})
                    # print(wh_div.text)
                    if i == 0:
                        webhooks['new_connection'] = wh_div.find('input')['value']
                        webhooks_activated.append('new_connection')
                    elif i == 1:
                        webhooks['new_message'] = wh_div.find('input')['value']
                        webhooks_activated.append('new_message')
                    elif i == 2:
                        webhooks['send_message'] = wh_div.find('input')['value']
                        webhooks_activated.append('send_message')

    return {
        "ok": True,
        "is_login": True,
        "has_account": True,
        "is_business": True,
        "ulinc_client_id": ulincid,
        "ulinc_is_active": True,
        "user_cookie": ulinc_cookie,
        "webhooks": webhooks,
        "webhooks_activated": webhooks_activated
    }

def main(request):
    if os.getenv('LOCAL_DEV'):
        request_json = request
    else:
        request_json = request.get_json()
    
    return get_ulinc_client_info(request_json['ulinc_username'], request_json['ulinc_password'], request_json['ulinc_li_email'])

if __name__ == '__main__':
    request = {
        "ulinc_username": "jhawkes20@gmail.com",
        "ulinc_password": "JA12345!",
        "ulinc_li_email": "jason@janium.io"
    }
    
    pprint(main(request))
