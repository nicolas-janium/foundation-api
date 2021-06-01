import base64
import json
import logging
import os
from datetime import datetime, timedelta
from pprint import pprint
from uuid import uuid4

import pytz
import requests
from nameparser import HumanName
from urllib3.exceptions import InsecureRequestWarning
from foundation_api import db
import foundation_api.V1.utils.demoji_module as demoji
from foundation_api.V1.sa_db.model import *

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning) # pylint: disable=no-member

mtn_tz = pytz.timezone('US/Mountain')
mtn_time = datetime.now(pytz.timezone('UTC')).astimezone(mtn_tz)

base_contact_dict = dict({
    'campaign_id': 0,
    'id': None,
    'first_name': None,
    'last_name': None,
    'title': None,
    'company': None,
    'location': None,
    'email': None,
    'phone': None,
    'website': None,
    'profile': None
})

def scrub_name(name):
    return HumanName(demoji.replace(name.replace(',', ''), ''))

def create_new_contact(contact_info, account_id, campaign_id, existing_ulinc_campaign_id, contact_source_id):
    data = {**base_contact_dict, **contact_info}
    name = scrub_name(data['first_name'] + ' ' + data['last_name'])
    return Contact(
        str(uuid4()),
        contact_source_id,
        account_id,
        campaign_id,
        existing_ulinc_campaign_id,
        data['id'],
        data['campaign_id'],
        {
            'ulinc': {
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'title': data['title'],
                'company': data['company'],
                'location': data['location'],
                'email': data['email'],
                'phone': data['phone'],
                'website': data['website'],
                'li_salesnav_profile_url': None,
                'li_profile_url': data['profile']
            }
        },
        None,
        User.system_user_id
    )

def poll_webhook(wh_url, webhook_type):
    try:
        if not os.getenv('FLASK_ENV') == 'development':
            return requests.get(wh_url, verify=False).json()
        else:
            f = open('./webhook_sample_data/{}.json'.format(webhook_type), 'r')
            return json.loads(f.read())
    except Exception as err:
        print('Error in polling this webhook url: {} \nError: {}'.format(wh_url, err))

def handle_webhook_response(account, contact_source_id):
    webhook_response = db.session.query(Contact_source).filter(Contact_source.contact_source_id == contact_source_id).first()
    for item in webhook_response.contact_source_json:
        existing_contact = db.session.query(Contact).filter(Contact.ulinc_id == str(item['id'])).first() # if contact exists in the contact table
        existing_ulinc_campaign = db.session.query(Ulinc_campaign).filter(Ulinc_campaign.account_id == account.account_id).filter(Ulinc_campaign.ulinc_ulinc_campaign_id == str(item['campaign_id'])).first()
        if webhook_response.contact_source_type_id == 1:
            if existing_contact: # if contact exists in the contact table
                # if len([action for action in existing_contact.actions if action.action_type_id == action_type_dict['ulinc_new_connection']['id']]) > 0:
                if existing_cnxn_action := existing_contact.actions.filter(Action.action_type_id == 1).first():
                    pass
                else:
                    existing_contact_info = existing_contact.contact_info
                    new_contact_info = {**base_contact_dict, **item}
                    existing_contact_info['ulinc']['email'] = new_contact_info['email']
                    existing_contact_info['ulinc']['phone'] = new_contact_info['phone']
                    existing_contact_info['ulinc']['website'] = new_contact_info['website']
                    existing_contact_info['ulinc']['li_profile_url'] = new_contact_info['profile']
                    existing_contact.contact_info = existing_contact_info
                    connection_action = Action(str(uuid4()), existing_contact.contact_id, 1, datetime.utcnow(), None, None)
                    db.session.add(connection_action)
            else:
                if existing_ulinc_campaign:
                    existing_ulinc_campaign_id = existing_ulinc_campaign.ulinc_campaign_id
                    if existing_ulinc_campaign.parent_janium_campaign:
                        janium_campaign_id = existing_ulinc_campaign.parent_janium_campaign.janium_campaign_id
                    else:
                        janium_campaign_id = Janium_campaign.unassigned_janium_campaign_id # Unassigned janium campaign id value
                else:
                    existing_ulinc_campaign_id = Ulinc_campaign.unassigned_ulinc_campaign_id
                    janium_campaign_id = Janium_campaign.unassigned_janium_campaign_id # Unassigned janium campaign id value
                
                new_contact = create_new_contact(item, account.account_id, janium_campaign_id, existing_ulinc_campaign_id, contact_source_id)
                connection_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow(), None, None)
                db.session.add(new_contact)
                db.session.add(connection_action)
        elif webhook_response.contact_source_type_id == 2:
            if existing_contact:
                contact_id = existing_contact.contact_id
                existing_contact_info = existing_contact.contact_info
                new_contact_info = {**base_contact_dict, **item}
                existing_contact_info['ulinc']['email'] = new_contact_info['email']
                existing_contact_info['ulinc']['phone'] = new_contact_info['phone']
                existing_contact_info['ulinc']['website'] = new_contact_info['website']
                existing_contact_info['ulinc']['li_profile_url'] = new_contact_info['profile']
                existing_contact.contact_info = existing_contact_info
            else:
                if existing_ulinc_campaign:
                    new_contact = create_new_contact(item, account.account_id, existing_ulinc_campaign.parent_janium_campaign.janium_campaign_id, existing_ulinc_campaign.ulinc_campaign_id, contact_source_id)
                else:
                    new_contact = create_new_contact(item, account.account_id, Janium_campaign.unassigned_janium_campaign_id, Ulinc_campaign.unassigned_ulinc_campaign_id, contact_source_id)
                db.session.add(new_contact)
                contact_id = new_contact.contact_id
            new_message_action = Action(
                str(uuid4()),
                contact_id,
                2,
                datetime.utcnow(),
                item['message'],
                None
            )
            db.session.add(new_message_action)
        elif webhook_response.contact_source_type_id == 3:
            if existing_contact:
                contact_id = existing_contact.contact_id
                existing_contact_info = existing_contact.contact_info
                new_contact_info = {**base_contact_dict, **item}
                existing_contact_info['ulinc']['email'] = new_contact_info['email']
                existing_contact_info['ulinc']['phone'] = new_contact_info['phone']
                existing_contact_info['ulinc']['website'] = new_contact_info['website']
                existing_contact_info['ulinc']['li_profile_url'] = new_contact_info['profile']
                existing_contact.contact_info = existing_contact_info
            else:
                if existing_ulinc_campaign:
                    new_contact = create_new_contact(item, account.account_id, existing_ulinc_campaign.parent_janium_campaign.janium_campaign_id, existing_ulinc_campaign.ulinc_campaign_id, contact_source_id)
                else:
                    new_contact = create_new_contact(item, account.account_id, Janium_campaign.unassigned_janium_campaign_id, Ulinc_campaign.unassigned_ulinc_campaign_id, contact_source_id)
                db.session.add(new_contact)
                contact_id = new_contact.contact_id

            if existing_ulinc_campaign:
                if existing_ulinc_campaign.parent_janium_campaign.is_messenger:
                    if existing_origin_message := db.session.query(Action).filter(Action.contact_id == contact_id).filter(Action.action_id == 13).first():
                        is_origin = False
                    else:
                        is_origin = True
                else:
                    is_origin = False
            else:
                is_origin = False

            if is_origin:
                new_action = Action(
                    str(uuid4()),
                    contact_id,
                    13,
                    datetime.utcnow(),
                    item['message'],
                    None
                )
            else:
                new_action = Action(
                    str(uuid4()),
                    contact_id,
                    3,
                    datetime.utcnow(),
                    item['message'],
                    None
                )
            db.session.add(new_action)
        else:
            print('Unknown webhook response type')
        db.session.commit()

def poll_ulinc_webhooks(account, ulinc_config):
    webhooks = [
        {"url": ulinc_config.new_connection_webhook, "type": 1},
        {"url": ulinc_config.new_message_webhook, "type": 2},
        {"url": ulinc_config.send_message_webhook, "type": 3}
    ]

    contact_source_id_list = []
    empty_webhook_responses = []
    for webhook in webhooks:
        webhook_request_response = poll_webhook(webhook['url'], webhook['type'])
        if len(webhook_request_response) > 0:
            contact_source = Contact_source(str(uuid4()), account.account_id, webhook['type'], webhook_request_response)
            # webhook_response = Webhook_response(str(uuid4()), account.account_id, webhook_request_response, webhook_response_type_dict[webhook['type']]['id'])
            db.session.add(contact_source)
            contact_source_id_list.append(contact_source.contact_source_id)
        else:
            empty_webhook_responses.append(webhook['type'])
    db.session.commit()
    print('Empty Webhooks for account {}: {}'.format(account.account_id, empty_webhook_responses))

    if len(contact_source_id_list) > 0:
        for contact_source_id in contact_source_id_list:
            handle_webhook_response(account, contact_source_id)
    print('Polled webhooks for {}'.format(account.account_id))


if __name__ == '__main__':
    account_id = "ccddacca-2106-46ea-911a-41c46040e60a"
    # main(account_id)
