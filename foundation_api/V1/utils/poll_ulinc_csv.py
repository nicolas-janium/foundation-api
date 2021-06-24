from datetime import datetime
from uuid import uuid4
import csv
import io

import requests
from nameparser import HumanName
from urllib3.exceptions import InsecureRequestWarning
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
            db.session.add(contact_source)
            db.session.commit()
            # return contact_source_id
            return "success"
        return "success"
    else:
        return "failure"
