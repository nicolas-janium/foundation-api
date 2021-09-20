import csv
import io
from unittest.mock import Mock
from uuid import uuid4

import requests
from flask import Response
from urllib3.exceptions import InsecureRequestWarning

from model import (Contact_source, Ulinc_config,
                   create_gcf_db_engine, create_gcf_db_session)

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning) # pylint: disable=no-member


def poll_and_save_webhook(ulinc_config, wh_url, wh_type, session):
    res = requests.get(wh_url, verify=False)
    if res.ok:
        if res_json := res.json():
            contact_source = Contact_source(str(uuid4()), ulinc_config.ulinc_config_id, wh_type, res_json)
            session.add(contact_source)
            session.commit()
            return True
        return True
    return None

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if ulinc_config := session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first():
            if ulinc_config.is_working:
                if poll_and_save_webhook(ulinc_config, json_body['webhook_url'], json_body['webhook_type'], session):
                    return Response("Success", 200) # Task should not repeat
                return Response("Unknown Error", 200) # Task should not repeat
            return Response("Ulinc_config not working", 200) # Task should not repeat
        return Response("Unknown ulinc_config_id", 200) # Task should not repeat


if __name__ == '__main__':
    data = {
        "ulinc_config_id": "d0b9f557-942c-4d5f-b986-8ff935ebce81",
        "webhook_url": "https://ulinc.co/zap/44cde3d9c69af6db363371e3c21286e3",
        "webhook_type": 3
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
