import os
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm.attributes import flag_modified

import requests
from foundation_api.V1.sa_db.model import *


def get_li_profile_id(li_profile_url):
    for part in str(li_profile_url).rsplit('/')[::-1]:
        if part:
            return part

def validate_kendo_email(email_addr):
    url = "https://kendoemailapp.com/verifyemail?apikey={}&email={}".format(os.getenv('KENDO_API_KEY'), email_addr)
    res = requests.get(url=url)
    print(res.text)
    if res.ok:
        return res.json()
    return None

def get_kendo_person(li_profile_id):
    url = "https://kendoemailapp.com/profilebylinkedin?apikey={}&linkedin={}".format(os.getenv('KENDO_API_KEY'), li_profile_id)
    res = requests.get(url=url)
    if res.ok:
        return res.json()
    return None

def data_enrichment_function(contact, session):
    contact_info = contact.contact_info
    li_profile_url = contact_info['ulinc']['li_profile_url']
    li_profile_id = get_li_profile_id(li_profile_url)
    kendo_person = get_kendo_person(li_profile_id)
    if kendo_person:
        action_id = str(uuid4())
        # if 'work_email' in kendo_person:
        #     if work_email := kendo_person['work_email']:
        #         work_email_dict = {
        #             "value": work_email,
        #             # "is_validated": True if validate_kendo_email(work_email) else False
        #             "is_validated": False
        #         }
        #         kendo_person['work_email'] = work_email_dict
        #         contact_info['kendo'] = kendo_person
        #         contact.contact_info = contact_info
        #         flag_modified(contact, 'contact_info')
        # if 'private_email' in kendo_person:
        #     if private_email := kendo_person['private_email']:
        #         private_email_dict = {
        #             "value": private_email,
        #             # "is_validated": True if validate_kendo_email(private_email) else False
        #             "is_validated": False
        #         }
        #         kendo_person['private_email'] = private_email_dict
        #         contact_info['kendo'] = kendo_person
        #         contact.contact_info = contact_info
        #         flag_modified(contact, 'contact_info')
        if 'kendo' not in contact_info:
            contact_info['kendo'] = kendo_person
            contact.contact_info = contact_info
            flag_modified(contact, 'contact_info')
            new_action = Action(action_id, contact.contact_id, 22, datetime.utcnow(), None)
            session.add(new_action)
            session.commit()
            return 'success'
        else:
            return 'success'
    return 'bad request'


if __name__ == '__main__':
    # jc = db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == '5598484a-2923-403f-bfdd-5a1e354792c7').first()
    # print(data_enrichment_function(jc))

    # get_kendo_person("brandongrant")
    print(get_li_profile_id('https://www.linkedin.com/in/bob-baader-1011ba2'))
    print(get_kendo_person(get_li_profile_id('https://www.linkedin.com/in/bob-baader-1011ba2')))

    # print(validate_kendo_email('dwschlais@gmail.com'))