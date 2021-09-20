from unittest.mock import Mock
from uuid import uuid4
from datetime import datetime

import requests
from flask import Response

from model import (Cookie, Ulinc_config, create_gcf_db_engine,
                   create_gcf_db_session)


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
        return "Bad Creds"
    return "Bad Request"

def refresh_ulinc_cookie(ulinc_config, session):
    ulinc_cookie = get_cookie(ulinc_config.credentials.username, ulinc_config.credentials.password)
    if ulinc_cookie == "Bad Request":
        return "Bad Request"
    elif ulinc_cookie == "Bad Creds":
        ulinc_config.is_working = False
        session.commit()
        return "Bad Creds"
    elif ulinc_cookie:
        if ulinc_config.cookie_id == Cookie.unassigned_cookie_id:
            new_cookie = Cookie(str(uuid4()), 1, ulinc_cookie)
            session.add(new_cookie)
            ulinc_config.cookie_id = new_cookie.cookie_id
        else:
            cookie = session.query(Cookie).filter(Cookie.cookie_id == ulinc_config.cookie_id).first()
            cookie.cookie_json_value = ulinc_cookie
        ulinc_config.is_working = True
        session.commit()
        return True
    else:
        ulinc_config.is_working = False
        session.commit()
        return None

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if ulinc_config := session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first():
            refresh_ulinc_cookie_response = refresh_ulinc_cookie(ulinc_config, session)
            if refresh_ulinc_cookie_response == "Bad Request":
                return Response("Bad Request. Try again", 300) # Task should repeat
            elif refresh_ulinc_cookie_response == "Bad Creds":
                return Response("Ulinc not working. Bad credentials", 200) # Task should not repeat
            elif refresh_ulinc_cookie_response:
                return Response("success", 200) # Task should not repeat
            else:
                return Response("Ulinc not working. Unknown error", 200) # Task should not repeat
        return Response("Unknown ulinc_config_id", 200) # Task should not repeat

if __name__ == '__main__':
    data = {"ulinc_config_id": "d0b9f557-942c-4d5f-b986-8ff935ebce81"}
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
