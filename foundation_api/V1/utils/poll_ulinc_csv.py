import base64
import json
import logging
import os
from datetime import datetime, timedelta
from pprint import pprint
from uuid import uuid4
import csv
import json
import io

import pytz
import requests
from nameparser import HumanName
from urllib3.exceptions import InsecureRequestWarning
from foundation_api import db
import foundation_api.V1.utils.demoji_module as demoji
from foundation_api.V1.sa_db.model import *

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning) # pylint: disable=no-member

base_contact_dict = dict({
    'Campaign ID': 0,
    'Contact ID': None,
    'Name': None,
    'Title': None,
    'Company': None,
    'Location': None,
    'Email': None,
    'Phone': None,
    'Website': None,
    'LinkedIn profile': None
})

def scrub_name(name):
    return HumanName(demoji.replace(name.replace(',', ''), ''))

def create_new_contact(contact_info, account_id, campaign_id, existing_ulinc_campaign_id, contact_source_id, ulinc_client_id):
    conv = lambda i : i or None
    data = {**base_contact_dict, **contact_info}
    name = scrub_name(data['Name'])
    return Contact(
        str(uuid4()),
        contact_source_id,
        account_id,
        campaign_id,
        existing_ulinc_campaign_id,
        str(ulinc_client_id + data['Contact ID']),
        data['Campaign ID'],
        {
            'ulinc': {
                'first_name': name.first,
                'last_name': name.last,
                'title': conv(data['Title']),
                'company': conv(data['Company']),
                'location': conv(data['Location']),
                'email': conv(data['Email']),
                'phone': conv(data['Phone']),
                'website': conv(data['Website']),
                'li_salesnav_profile_url': data['LinkedIn profile'] if 'sales' in data['LinkedIn profile'] else None,
                'li_profile_url': data['LinkedIn profile'] if 'sales' not in data['LinkedIn profile'] else None
            }
        },
        None,
        User.system_user_id
    )


def poll_and_save_csv(ulinc_config, ulinc_campaign):
    header = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    cookie = ulinc_config.cookie.cookie_json_value
    usr = cookie['usr']
    pwd = cookie['pwd']
    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', usr)
    jar.set('pwd', pwd)

    data = {"status": "1", "id": "{}".format(ulinc_campaign.ulinc_campaign_id)}

    res = requests.post(url='https://ulinc.co/{}/campaigns/{}/?do=campaigns&act=export'.format(ulinc_config.ulinc_client_id, ulinc_campaign.ulinc_ulinc_campaign_id), headers=header, data=data, cookies=jar)
    if res.ok:
        reader = csv.DictReader(io.StringIO(res.content.decode('utf-8')))
        contact_source_id = str(uuid4())
        if csv_data := list(reader):
            contact_source = Contact_source(contact_source_id, ulinc_config.account_id, 4, csv_data)
            db.session.add(contact_source)
            db.session.commit()
            return contact_source_id
        print(res.text)
        return None
    else:
        return None



def handle_csv_data(account, ulinc_config):
    for ulinc_campaign in ulinc_config.ulinc_campaigns:
        janium_campaign = ulinc_campaign.parent_janium_campaign
        contact_source_id = poll_and_save_csv(ulinc_config.ulinc_client_id, ulinc_campaign.ulinc_ulinc_campaign_id, ulinc_config.cookie.cookie_json_value,  account.account_id)
        d_list = db.session.query(Contact_source).filter(Contact_source.contact_source_id == contact_source_id).first().contact_source_json

        if d_list:
            print('Length of csv export: {}'.format(len(d_list)))
            for item in d_list:
                existing_contact = db.session.query(Contact).filter(Contact.ulinc_id == str(ulinc_config.ulinc_client_id + item['Contact ID'])).first()
                # existing_contact = db.session.query(Contact).filter(Contact.ulinc_id == str('5676186' + item['Contact ID'])).first()
                if item['Status'] == 'In Queue':
                    if existing_contact:
                        if existing_action := existing_contact.actions.filter(Action.action_type_id == 18).first():
                            continue
                        else:
                            new_action = Action(str(uuid4()), existing_contact.contact_id, 18, datetime.utcnow(), None)
                            db.session.add(new_action)
                    else:
                        new_contact = create_new_contact(
                            item, account.account_id, janium_campaign.janium_campaign_id, ulinc_campaign.ulinc_campaign_id, contact_source_id, ulinc_config.ulinc_client_id
                        )
                        db.session.add(new_contact)
                        new_action = Action(str(uuid4()), new_contact.contact_id, 18, datetime.utcnow(), None)
                        db.session.add(new_action)
                elif item['Status'] == 'Connect Req':
                    if existing_contact:
                        if existing_action := existing_contact.actions.filter(Action.action_type_id == 19).first():
                            continue
                        else:
                            existing_contact_info = existing_contact.contact_info
                            existing_contact_info['li_profile_url'] = item['LinkedIn profile']
                            existing_contact.contact_info = existing_contact_info
                            new_action = Action(str(uuid4()), existing_contact.contact_id, 19, datetime.utcnow(), None)
                            db.session.add(new_action)
                    else:
                        new_contact = create_new_contact(
                            item, account.account_id, janium_campaign.janium_campaign_id, ulinc_campaign.ulinc_campaign_id, contact_source_id, ulinc_config.ulinc_client_id
                        )
                        db.session.add(new_contact)
                        new_action = Action(str(uuid4()), new_contact.contact_id, 19, datetime.utcnow(), None)
                        db.session.add(new_action)
                elif item['Status'] == 'Connect Error':
                    if existing_contact:
                        if existing_action := existing_contact.actions.filter(Action.action_type_id == 20).first():
                            continue
                        else:
                            new_action = Action(str(uuid4()), existing_contact.contact_id, 20, datetime.utcnow(), None)
                            db.session.add(new_action)
                    else:
                        new_contact = create_new_contact(
                            item, account.account_id, janium_campaign.janium_campaign_id, ulinc_campaign.ulinc_campaign_id, contact_source_id, ulinc_config.ulinc_client_id
                        )
                        db.session.add(new_contact)
                        new_action = Action(str(uuid4()), new_contact.contact_id, 20, datetime.utcnow(), None)
                        db.session.add(new_action)
                elif item['Status'] == 'Later':
                    if existing_contact:
                        if existing_action := existing_contact.actions.filter(Action.action_type_id == 21).first():
                            continue
                        else:
                            new_action = Action(str(uuid4()), existing_contact.contact_id, 21, datetime.utcnow(), None)
                            db.session.add(new_action)
                    else:
                        new_contact = create_new_contact(
                            item, account.account_id, janium_campaign.janium_campaign_id, ulinc_campaign.ulinc_campaign_id, contact_source_id, ulinc_config.ulinc_client_id
                        )
                        db.session.add(new_contact)
                        new_action = Action(str(uuid4()), new_contact.contact_id, 21, datetime.utcnow(), None)
                        db.session.add(new_action)
                elif item['Status'] == 'No Interest':
                    if existing_contact:
                        if existing_action := existing_contact.actions.filter(Action.action_type_id == 11).first():
                            continue
                        else:
                            new_action = Action(str(uuid4()), existing_contact.contact_id, 11, datetime.utcnow(), None)
                            db.session.add(new_action)
                    else:
                        new_contact = create_new_contact(
                            item, account.account_id, janium_campaign.janium_campaign_id, ulinc_campaign.ulinc_campaign_id, contact_source_id, ulinc_config.ulinc_client_id
                        )
                        db.session.add(new_contact)
                        new_action = Action(str(uuid4()), new_contact.contact_id, 11, datetime.utcnow(), None)
                        db.session.add(new_action)
                elif item['Status'] == 'Connected':
                    if existing_contact:
                        if existing_cnxn_action := existing_contact.actions.filter(Action.action_type_id.in_([1])).first():
                            if stop_campaign_actions := existing_contact.actions.filter(Action.action_type_id.in_([2, 6, 11, 21])).order_by(Action.action_timestamp.desc()).all():
                                if continue_campaign_action := existing_contact.actions.filter(Action.action_type_id == 14).order_by(Action.action_timestamp.desc()).first():
                                    if stop_campaign_actions[0].action_timestamp > continue_campaign_action.action_timestamp:
                                        new_action = Action(str(uuid4()), existing_contact.contact_id, 14, datetime.utcnow(), None)
                                        db.session.add(new_action)
                                    else:
                                        continue
                                else:
                                    new_action = Action(str(uuid4()), existing_contact.contact_id, 14, datetime.utcnow(), None)
                                    db.session.add(new_action)
                            else:
                                continue
                        else:
                            new_action = Action(str(uuid4()), existing_contact.contact_id, 1, datetime.utcnow(), None)
                            db.session.add(new_action)
                    else:
                        new_contact = create_new_contact(
                            item, account.account_id, janium_campaign.janium_campaign_id, ulinc_campaign.ulinc_campaign_id, contact_source_id, ulinc_config.ulinc_client_id
                        )
                        db.session.add(new_contact)
                        new_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow(), None)
                        db.session.add(new_action)
                elif item['Status'] == 'Replied':
                    if existing_contact:
                        if existing_cnxn_action := existing_contact.actions.filter(Action.action_type_id == 1).first():
                            pass
                        else:
                            cnxn_action = Action(str(uuid4()), existing_contact.contact_id, 1, datetime.utcnow(), None)
                            db.session.add(cnxn_action)
                    else:
                        new_contact = create_new_contact(
                            item, account.account_id, janium_campaign.janium_campaign_id, ulinc_campaign.ulinc_campaign_id, contact_source_id, ulinc_config.ulinc_client_id
                        )
                        db.session.add(new_contact)
                        new_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow(), None)
                        db.session.add(new_action)
                elif item['Status'] == 'Talking':
                    if existing_contact:
                        if existing_cnxn_action := existing_contact.actions.filter(Action.action_type_id == 1).first():
                            pass
                        else:
                            cnxn_action = Action(str(uuid4()), existing_contact.contact_id, 1, datetime.utcnow(), None)
                            db.session.add(cnxn_action)
                    else:
                        new_contact = create_new_contact(
                            item, account.account_id, janium_campaign.janium_campaign_id, ulinc_campaign.ulinc_campaign_id, contact_source_id, ulinc_config.ulinc_client_id
                        )
                        db.session.add(new_contact)
                        new_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow(), None)
                        db.session.add(new_action)
            db.session.commit()

if __name__ == '__main__':
    account_id = "ccddacca-2106-46ea-911a-41c46040e60a"
    main(account_id)
