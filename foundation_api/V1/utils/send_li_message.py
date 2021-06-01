import base64
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pprint import pprint
from typing import final
from uuid import uuid4
import pytz
import math

import requests
import urllib3
from urllib import parse
from bs4 import BeautifulSoup as Soup
from html2text import html2text
from sqlalchemy import or_, and_
from workdays import networkdays
from foundation_api import db
from foundation_api.V1.sa_db.model import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('send_li_message')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
logHandler = logging.StreamHandler()
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

def send_li_message(details):
    req_session = requests.Session()
    url = 'https://ulinc.co/{}/campaigns/{}/?do=campaigns&act=send_message'.format(details['ulinc_client_id'], int(details['ulinc_campaign_id']))

    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', details['cookie_usr'])
    jar.set('pwd', details['cookie_pwd'])

    headers = {
        "Accept": "application/json"
    }

    message = str(details['message_text'])
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
        "message[text]": final_message
    }

    res = req_session.post(url=url, cookies=jar, headers=headers, data=payload, verify=False)
    if res.ok:
        res_json = res.json()
        if res_json['status'] == 'ok':
            # print("Sent li message to contact {} for client {}".format(details['contactid'], details['client_fullname']))

            status_url = "https://ulinc.co/{}/campaigns/{}/?do=campaigns&act=continue_sending&id={}".format(details['ulinc_client_id'], int(details['ulinc_campaign_id']), details['contact_ulinc_id'])
            status_res = req_session.get(url=status_url, cookies=jar, headers=headers, verify=False)
            if status_res.ok:
                # print("Updated Ulinc status to connected for contact {} for client {}".format(details['contactid'], details['client_fullname']))
                return details['contact_id']
            else:
                print("Failed to update status to connected for contact {} at request level. Response: {}".format(details['contact_id'], res.text))
                return details['contact_id']
        else:
            print("Li message to contact {} failed. Response: {}".format(details['contact_id'], res.text))
            return None
    else:
        print("Li message to contact {} failed at request level. Response: {}".format(details['contact_id'], res.text))
        return None

def get_li_message_targets(account, ulinc_config, janium_campaign, account_local_time):
    # steps = janium_campaign.janium_campaign_steps.filter(Janium_campaign_step.janium_campaign_step_type_id == 1).order_by(Janium_campaign_step.janium_campaign_step_delay).all()
    steps = janium_campaign.janium_campaign_steps.filter(Janium_campaign_step.janium_campaign_step_type_id != 4).order_by(Janium_campaign_step.janium_campaign_step_delay).all()

    contacts = [
        contact 
        for contact 
        in janium_campaign.contacts.all()
        if not contact.actions.filter(Action.action_type_id.in_([7,11])).first()
    ]

    li_message_targets_list = []
    for contact in contacts:
        if previous_received_messages := contact.actions.filter(Action.action_type_id.in_([2, 6, 11, 21])).order_by(Action.action_timestamp.desc()).all():
            if continue_campaign_action := contact.actions.filter(Action.action_type_id == 14).order_by(Action.action_timestamp.desc()).first():
                if previous_received_messages[0].action_timestamp > continue_campaign_action.action_timestamp:
                    continue
            else:
                continue

        if cnxn_action := contact.actions.filter(Action.action_type_id == 1).order_by(Action.action_timestamp.desc()).first():
            li_messages = contact.actions.filter(Action.action_type_id == 3).filter(Action.action_timestamp >= cnxn_action.action_timestamp).order_by(Action.action_timestamp.desc()).all()
            num_li_messages = len(li_messages) if li_messages else 0
            last_li_message = li_messages[0] if li_messages else None

            if continue_campaign_action := contact.actions.filter(Action.action_type_id == 14).order_by(Action.action_timestamp.desc()).first():
                cnxn_timestamp = cnxn_action.action_timestamp
                if last_li_message:
                    days_to_add = networkdays(last_li_message.action_timestamp, continue_campaign_action.action_timestamp) - 1
                else:
                    days_to_add = networkdays(previous_received_messages[0].action_timestamp, continue_campaign_action.action_timestamp) - 1
                while days_to_add > 0:
                    cnxn_timestamp += timedelta(days=1)
                    if cnxn_timestamp.weekday() >= 5: # sunday = 6
                        continue
                    days_to_add -= 1
            else:
                cnxn_timestamp = cnxn_action.action_timestamp

            cnxn_timestamp = pytz.utc.localize(cnxn_timestamp).astimezone(pytz.timezone(account.time_zone.time_zone_code)).replace(tzinfo=None)
            day_diff = networkdays(cnxn_timestamp, account_local_time) - 1

            for i, step in enumerate(steps):
                add_contact = False
                if step.janium_campaign_step_type_id == 1:
                    if i + 1 < len(steps):
                        if step.janium_campaign_step_delay <= day_diff:
                        # if step.janium_campaign_step_delay <= day_diff < steps[i + 1].janium_campaign_step_delay:
                            if num_li_messages < i + 1:
                                add_contact = True
                                body = step.janium_campaign_step_body
                                break
                            else:
                                continue
                        else: 
                            continue
                    else:
                        # if step.janium_campaign_step_delay <= day_diff <= step.janium_campaign_step_delay + 1:
                        if step.janium_campaign_step_delay <= day_diff:
                            if num_li_messages < i + 1:
                                add_contact = True
                                body = step.janium_campaign_step_body
                                break
                            else:
                                continue
                        else:
                            continue
        if add_contact:
            li_message_targets_list.append(
                {
                    "ulinc_client_id": ulinc_config.ulinc_client_id,
                    "contact_id": contact.contact_id,
                    "contact_first_name": contact.contact_info['ulinc']['first_name'],
                    "contact_ulinc_id": str(contact.ulinc_id).replace(str(ulinc_config.ulinc_client_id), ''),
                    "message_text": str(body).replace(r"{FirstName}", contact.contact_info['ulinc']['first_name']),
                    "ulinc_campaign_id": contact.ulinc_ulinc_campaign_id,
                    "cookie_usr": ulinc_config.cookie.cookie_json_value['usr'],
                    "cookie_pwd": ulinc_config.cookie.cookie_json_value['pwd']
                }
            )
    return li_message_targets_list

def send_li_message_function(account, ulinc_config, janium_campaign, account_local_time, queue_times_dict):
    # print("inside send_li_message_function")
    li_message_targets_list = get_li_message_targets(account, ulinc_config, janium_campaign, account_local_time)
    # pprint(li_message_targets_list)

    ### Divide the email targets list to evenly distribute over the queue start and end time ###
    queue_intervals = int((queue_times_dict['end'].hour - queue_times_dict['start'].hour) / 0.5)
    queue_max = math.ceil(len(li_message_targets_list) / queue_intervals)

    recipient_list = []
    for li_message_target in li_message_targets_list[0:queue_max]:
        res = send_li_message(li_message_target)
        if res:
            recipient_list.append({"contact_id": res})
            action = Action(str(uuid4()), res, 3, datetime.utcnow(), li_message_target['message_text'])
            db.session.add(action)
            db.session.commit()
    return recipient_list


if __name__ == '__main__':
    payload = {
        "account_id": "ccddacca-2106-46ea-911a-41c46040e60a"
    }
    payload = json.dumps(payload)
    payload = base64.b64encode(str(payload).encode("utf-8"))
    event = {
        "data": payload
    }
    send_li_message_function(event, 1)
