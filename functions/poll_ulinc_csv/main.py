from unittest.mock import Mock
from uuid import uuid4
import io
import csv

import requests
from flask import Response

from model import (Contact_source, Ulinc_config, Ulinc_campaign,
                   create_gcf_db_engine, create_gcf_db_session)


def poll_and_save_csv(ulinc_config, ulinc_campaign, session):
    header = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    ulinc_cookie = ulinc_config.cookie.cookie_json_value
    usr = ulinc_cookie['usr']
    pwd = ulinc_cookie['pwd']
    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', usr)
    jar.set('pwd', pwd)

    data = {"status": "1", "id": "{}".format(ulinc_campaign.ulinc_campaign_id)}

    res = requests.post(url='https://ulinc.co/{}/campaigns/{}/?do=campaigns&act=export'.format(ulinc_config.ulinc_client_id, ulinc_campaign.ulinc_ulinc_campaign_id), headers=header, data=data, cookies=jar)
    if res.ok:
        reader = csv.DictReader(io.StringIO(res.content.decode('utf-8')))
        contact_source_id = str(uuid4())
        if csv_data := list(reader):
            contact_source = Contact_source(contact_source_id, ulinc_config.ulinc_config_id, 4, csv_data)
            session.add(contact_source)
            session.commit()
            # return contact_source_id
            return True
        return True
    return None

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if ulinc_config := session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first():
            if ulinc_config.is_working:
                if ulinc_campaign := session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_campaign_id == json_body['ulinc_campaign_id']).first():
                    if poll_and_save_csv(ulinc_config, ulinc_campaign, session):
                        return Response("Success", 200) # Task should not repeat
                    return Response("Unknown Error", 200) # Task should not repeat
                return Response("Unknown ulinc_campaign_id", 200) # Task should not repeat
            return Response("Ulinc_config not working", 200) # Task should not repeat
        return Response("Unknown ulinc_config_id", 200) # Task should not repeat


if __name__ == '__main__':
    data = {
        "ulinc_config_id": "d0b9f557-942c-4d5f-b986-8ff935ebce81",
        "ulinc_campaign_id": "753d27be-c5e5-4b12-806d-b9bf60ccab5f"
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
