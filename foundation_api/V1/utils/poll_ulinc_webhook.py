from datetime import datetime
from uuid import uuid4
import json

import pytz
import requests
from nameparser import HumanName
from urllib3.exceptions import InsecureRequestWarning
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

def poll_and_save_webhook(ulinc_config, wh_url, wh_type):
    res = requests.get(wh_url, verify=False)
    if res.ok:
        if res_json := res.json():
            contact_source = Contact_source(str(uuid4()), ulinc_config.ulinc_config_id, wh_type, res_json)
            db.session.add(contact_source)
            db.session.commit()
            return "success"
        print("Webhook is empty")
        return "success"
    return "failure"
