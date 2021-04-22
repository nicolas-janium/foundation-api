import base64
import csv
import io
import json
import logging
import os
from datetime import datetime, timedelta
from pprint import pprint
from uuid import uuid4
from sqlalchemy.orm.attributes import flag_modified


import pytz
import requests
from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.sa_db.model import *
from workdays import networkdays

def get_li_profile_id(li_profile_url):
    for part in str(li_profile_url).rsplit('/')[::-1]:
        if part:
            return part

def validate_kendo_email(email_addr):
    url = "https://kendoemailapp.com/verifyemail?apikey={}&email={}".format(os.getenv('KENDO_API_KEY'), email_addr)
    res = requests.get(url=url)
    if res.ok:
        return res.json()

def get_kendo_person(li_profile_id):
    url = "https://kendoemailapp.com/profilebylinkedin?apikey={}&linkedin={}".format(os.getenv('KENDO_API_KEY'), li_profile_id)
    res = requests.get(url=url)
    if res.ok:
        return res.json()

def data_enrichment_function(account):
    account_local_time = datetime.now(pytz.timezone('UTC')).astimezone(pytz.timezone(account.time_zone.time_zone_code)).replace(tzinfo=None)
    enriched_contacts = []
    for janium_campaign in account.janium_campaigns:
        for contact in janium_campaign.contacts:
            # print(contact.contact_id)
            contact_info = contact.contact_info
            if cnxn_action := contact.actions.filter(Action.action_type_id == 1).first():
                continue
            elif cnxn_req_action := contact.actions.filter(Action.action_type_id == 19).first():
                # print(contact.contact_id)
                if kendo_de_action := contact.actions.filter(Action.action_type_id == 22).first():
                    continue
                else:
                    if campaign_steps := janium_campaign.janium_campaign_steps.filter(Janium_campaign_step.janium_campaign_step_type_id == 4).order_by(Janium_campaign_step.janium_campaign_step_delay).all():
                        if (networkdays(cnxn_req_action.action_timestamp, datetime.utcnow()) - 1) >= (campaign_steps[0].janium_campaign_step_delay - 1):
                            if li_profile_url := contact_info['ulinc']['li_profile_url']:
                                li_profile_id = get_li_profile_id(li_profile_url)
                                kendo_person = get_kendo_person(li_profile_id)
                                # print(li_profile_id)
                                # print(kendo_person)
                                action_id = str(uuid4())
                                if work_email := kendo_person['work_email']:
                                    work_email_dict = {
                                        "value": work_email,
                                        "is_validated": True if validate_kendo_email(work_email) else False 
                                    }
                                    kendo_person['work_email'] = work_email_dict
                                    contact_info['kendo'] = kendo_person
                                    contact.contact_info = contact_info
                                    flag_modified(contact, 'contact_info')
                                    if new_action := db.session.query(Action).filter(Action.action_id == action_id).first():
                                        pass
                                    else:
                                        new_action = Action(action_id, contact.contact_id, 22, datetime.utcnow(), None)
                                        db.session.add(new_action)
                                    db.session.commit()
                                    enriched_contacts.append(
                                        {"janium_campaign_id": janium_campaign.janium_campaign_id, "contact_id": contact.contact_id}
                                    )
                                if private_email := kendo_person['private_email']:
                                    private_email_dict = {
                                        "value": private_email,
                                        "is_validated": True if validate_kendo_email(private_email) else False
                                    }
                                    kendo_person['private_email'] = private_email_dict
                                    contact_info['kendo'] = kendo_person
                                    contact.contact_info = contact_info
                                    flag_modified(contact, 'contact_info')
                                    if new_action := db.session.query(Action).filter(Action.action_id == action_id).first():
                                        pass
                                    else:
                                        new_action = Action(action_id, contact.contact_id, 22, datetime.utcnow(), None)
                                        db.session.add(new_action)
                                    db.session.commit()
                                    enriched_contacts.append(
                                        {"janium_campaign_id": janium_campaign.janium_campaign_id, "contact_id": contact.contact_id}
                                    )
            else:
                pass
    return enriched_contacts

if __name__ == '__main__':
    account_id = "ccddacca-2106-46ea-911a-41c46040e60a"

    account = db.session.query(Account).filter(Account.account_id == account_id).first()
    print(data_enrichment_function(account))
    # get_kendo_person("brandongrant")
    # print(get_li_profile_id('https://www.linkedin.com/in/bob-baader-1011ba2'))
    # print(get_kendo_person(get_li_profile_id('https://www.linkedin.com/in/bob-baader-1011ba2')))
