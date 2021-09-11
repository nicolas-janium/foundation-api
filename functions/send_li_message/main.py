import json
import os
from unittest.mock import Mock
from uuid import uuid4
from datetime import datetime, timedelta

import requests
import urllib3
from bs4 import BeautifulSoup as Soup
from flask import Response
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from urllib3.exceptions import InsecureRequestWarning

from model import (Contact, Contact_source, Janium_campaign_step,
                   Ulinc_campaign, Ulinc_config, create_gcf_db_engine,
                   create_gcf_db_session)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning) # pylint: disable=no-member


def poll_and_save_webhook(ulinc_config, wh_url, wh_type, session):
    res = requests.get(wh_url, verify=False)
    if res.ok:
        if res_json := res.json():
            contact_source = Contact_source(str(uuid4()), ulinc_config.ulinc_config_id, wh_type, res_json)
            session.add(contact_source)
            session.commit()
            return "Webhook response saved"
        return "Webhook response empty"
    return "Bad request"

 
def insert_key_words(email_html, key_words_dict):
    email_html = str(email_html)
    for key in key_words_dict:
        key_string = str('{' + key + '}')
        if key_string in email_html:
            email_html = email_html.replace(key_string, key_words_dict[key])
    return email_html

def send_li_message(ulinc_config, janium_campaign_step, ulinc_campaign, contact):
    req_session = requests.Session()
    url = 'https://ulinc.co/{}/campaigns/{}/?do=campaigns&act=send_message'.format(ulinc_config.ulinc_client_id, int(ulinc_campaign.ulinc_ulinc_campaign_id))

    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', ulinc_config.cookie.cookie_json_value['usr'])
    jar.set('pwd', ulinc_config.cookie.cookie_json_value['pwd'])

    headers = {
        "Accept": "application/json"
    }

    key_words_dict = contact.create_key_words_dict()

    message = str(janium_campaign_step.janium_campaign_step_body)
    message = insert_key_words(message, key_words_dict=key_words_dict)
    soup = Soup(message, 'html.parser')
    final_message = ''
    for i, p in enumerate(soup.find_all('p')):
        if i == 0:
            final_message += p.get_text('\n')
        else:
            final_message += "\n\n"
            final_message += p.get_text('\n')

    payload = {
        "message[contact_id]": contact.get_short_ulinc_id(ulinc_config.ulinc_client_id),
        "message[text]": final_message if len(final_message) > 0 else message
    }

    res = req_session.post(url=url, cookies=jar, headers=headers, data=payload, verify=False)
    if res.ok:
        res_json = res.json()
        if res_json['status'] == 'ok':
            return "Success"
        return {"error_message": "Error at Ulinc level. Error message: {}".format(res_json)}
    return {"error_message": "Error at request level. Error message: {}".format(res.text)}

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        gct_client = tasks_v2.CloudTasksClient()
        gct_parent = gct_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='update-ulinc-contact-status')
        if ulinc_config := session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first():
            if janium_campaign_step := session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == json_body['janium_campaign_step_id']).first():
                if ulinc_campaign := session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_campaign_id == json_body['ulinc_campaign_id']).first():
                    if contact := session.query(Contact).filter(Contact.contact_id == json_body['contact_id']).first():
                        if contact.is_messaging_task_valid():
                            webhook_response = poll_and_save_webhook(ulinc_config, ulinc_config.new_message_webhook, 2, session)
                            if webhook_response == 'Webhook response saved':
                                payload = json_body
                                task = {
                                    "http_request": {  # Specify the type of request.
                                        "http_method": tasks_v2.HttpMethod.POST,
                                        "url": os.getenv('SEND_LI_MESSAGE_TRIGGER_URL'),
                                        'body': json.dumps(payload).encode(),
                                        'headers': {
                                            'Content-type': 'application/json'
                                        }
                                    }
                                }

                                # Add the timestamp to the tasks.
                                timestamp = timestamp_pb2.Timestamp()
                                timestamp.FromDatetime(datetime.utcnow() + timedelta(minutes=15))
                                task['schedule_time'] = timestamp

                                gct_send_parent = gct_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send-li-message')
                                task_response = gct_client.create_task(parent=gct_send_parent, task=task)
                                return Response('New message webhook response was not empty. Created new task', 200)

                            elif webhook_response == 'Webhook response empty':
                                send_li_message_res = send_li_message(ulinc_config, janium_campaign_step, ulinc_campaign, contact)
                                if send_li_message_res == 'Success':
                                    payload = {
                                        "ulinc_config_id": ulinc_config.ulinc_config_id,
                                        "ulinc_campaign_id": ulinc_campaign.ulinc_campaign_id,
                                        "contact_id": contact.contact_id
                                    }
                                    task = {
                                        "http_request": {  # Specify the type of request.
                                            "http_method": tasks_v2.HttpMethod.POST,
                                            "url": os.getenv('UPDATE_ULINC_CONTACT_STATUS_TRIGGER_URL'),
                                            'body': json.dumps(payload).encode(),
                                            'headers': {
                                                'Content-type': 'application/json'
                                            }
                                        }
                                    }
                                    task_response = gct_client.create_task(parent=gct_parent, task=task)
                                    return Response('Success', 200)
                                else:
                                    return Response(send_li_message_res['error_message'], 200) # Should not retry
                            else:
                                pass
                        return Response("Messaging task no longer valid", 200)
                    return Response("Unknown contact_id", 200)
                return Response("Unknown ulinc_campaign_id", 200)
            return Response("Unknown janium_campaign_step_id", 200)
        return Response("Unknown ulinc_config_id", 200)


if __name__ == '__main__':
    data = {
        "ulinc_config_id": "d0b9f557-942c-4d5f-b986-8ff935ebce81",
        "janium_campaign": "5598484a-2923-403f-bfdd-5a1e354792c7",
        "janium_campaign_step_id": "7fc67976-953b-4c1d-8902-3035932b7287",
        "ulinc_campaign_id": "08f1ffec-f040-40b3-a9cf-367be36f037a",
        "contact_id": "00001317-1c52-40ba-a8eb-04be0998a180"
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
