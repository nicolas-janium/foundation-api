import base64
import json
import logging
from datetime import datetime, timedelta
from uuid import uuid4
import pytz
import math

import requests
import urllib3
from bs4 import BeautifulSoup as Soup
from workdays import networkdays
from foundation_api.V1.sa_db.model import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('send_li_message')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
logHandler = logging.StreamHandler()
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

def send_li_message_function(details):
    req_session = requests.Session()
    url = 'https://ulinc.co/{}/campaigns/{}/?do=campaigns&act=send_message'.format(details['ulinc_client_id'], int(details['ulinc_ulinc_campaign_id']))

    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', details['cookie_usr'])
    jar.set('pwd', details['cookie_pwd'])

    headers = {
        "Accept": "application/json"
    }

    message = str(details['message_body'])
    soup = Soup(message, 'html.parser')
    final_message = ''
    for i, p in enumerate(soup.find_all('p')):
        if i == 0:
            final_message += p.get_text('\n')
        else:
            final_message += "\n\n"
            final_message += p.get_text('\n')

    # final_message = parse.quote_plus(final_message)

    payload = {
        "message[contact_id]": details['contact_ulinc_id'],
        "message[text]": final_message if len(final_message) > 0 else message
    }

    res = req_session.post(url=url, cookies=jar, headers=headers, data=payload, verify=False)
    if res.ok:
        res_json = res.json()
        if res_json['status'] == 'ok':
            return "Message sent"
        else:
            print("Li message to contact {} failed. Response: {}".format(details['contact_id'], res.text))
            return None
    else:
        print("Li message to contact {} failed at request level. Response: {}".format(details['contact_id'], res.text))
        return None

def update_ulinc_contact_status(details):
    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', details['cookie_usr'])
    jar.set('pwd', details['cookie_pwd'])
    status_url = "https://ulinc.co/{}/campaigns/{}/?do=campaigns&act=continue_sending&id={}".format(details['ulinc_client_id'], int(details['ulinc_ulinc_campaign_id']), details['contact_ulinc_id'])
    status_res = requests.get(url=status_url, cookies=jar, verify=False)
    if status_res.ok:
        return "Ulinc contact updated"

# def send_li_message_function(account, ulinc_config, janium_campaign, account_local_time, queue_times_dict):
#     # print("inside send_li_message_function")
#     li_message_targets_list = get_li_message_targets(account, ulinc_config, janium_campaign, account_local_time)
#     # pprint(li_message_targets_list)

#     ### Divide the email targets list to evenly distribute over the queue start and end time ###
#     queue_intervals = int((queue_times_dict['end'].hour - queue_times_dict['start'].hour) / 0.5)
#     queue_max = math.ceil(len(li_message_targets_list) / queue_intervals)

#     recipient_list = []
#     for li_message_target in li_message_targets_list[0:queue_max]:
#         res = send_li_message(li_message_target)
#         if res:
#             recipient_list.append({"contact_id": res})
#             action = Action(str(uuid4()), res, 3, datetime.utcnow(), li_message_target['message_text'])
#             db.session.add(action)
#             db.session.commit()
#     return recipient_list


if __name__ == '__main__':
    email_target_details= {
        "contact_first_name": "Keith",
        "contact_full_name": "Keith Lovegrove",
        "contact_id": "00001317-1c52-40ba-a8eb-04be0998a180",
        "contact_ulinc_id": 1868,
        "cookie_pwd": "93fd3060131f8f9e8410775809f0a231",
        "cookie_usr": "48527",
        "janium_campaign_id": "5598484a-2923-403f-bfdd-5a1e354792c7",
        "message_body": "Li Message Body",
        "ulinc_client_id": "5676186",
        "ulinc_ulinc_campaign_id": 7
    }
    print(send_li_message_function(email_target_details))