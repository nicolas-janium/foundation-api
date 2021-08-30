from unittest.mock import Mock

import requests
import urllib3
from flask import Response

from model import (Contact, Ulinc_config, Ulinc_campaign, Janium_campaign_step, create_gcf_db_engine,
                   create_gcf_db_session)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def update_ulinc_contact_status(ulinc_config, ulinc_campaign, contact):
    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', ulinc_config.cookie.cookie_json_value['usr'])
    jar.set('pwd', ulinc_config.cookie.cookie_json_value['pwd'])
    status_url = "https://ulinc.co/{}/campaigns/{}/?do=campaigns&act=continue_sending&id={}".format(ulinc_config.ulinc_client_id, int(ulinc_campaign.ulinc_ulinc_campaign_id), contact.get_short_ulinc_id(ulinc_config.ulinc_client_id))
    status_res = requests.get(url=status_url, cookies=jar, verify=False)
    if status_res.ok:
        return "Success"
    return {"error_message": "Error at request level. Error message: {}".format(status_res.text)}

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if ulinc_config := session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first():
            if ulinc_campaign := session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_campaign_id == json_body['ulinc_campaign_id']).first():
                if contact := session.query(Contact).filter(Contact.contact_id == json_body['contact_id']).first():
                    update_ulinc_contact_status_res = update_ulinc_contact_status(ulinc_config, ulinc_campaign, contact)
                    if update_ulinc_contact_status_res == 'Success':
                        return Response('Success', 200)
                    else:
                        return Response(update_ulinc_contact_status_res['error_message'], 200) # Should not retry
                return Response("Unknown contact_id", 200)
            return Response("Unknown ulinc_campaign_id", 200)
        return Response("Unknown ulinc_config_id", 200)

if __name__ == '__main__':
    data = {
        "ulinc_config_id": "d0b9f557-942c-4d5f-b986-8ff935ebce81",
        "ulinc_campaign_id": "08f1ffec-f040-40b3-a9cf-367be36f037a",
        "contact_id": "00001317-1c52-40ba-a8eb-04be0998a180"
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
