import os
from datetime import datetime
from email.header import Header
from unittest.mock import Mock
from uuid import uuid4
import json

import requests
from sqlalchemy.orm.attributes import flag_modified
from flask import Response

from model import (Contact, Action, create_gcf_db_engine,
                   create_gcf_db_session)

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
    url = "https://kendoemailapp.com/emailbylinkedin?apikey={}&linkedin={}".format(os.getenv('KENDO_API_KEY'), li_profile_id)
    print(url)
    res = requests.get(url=url)
    if res.ok:
        return res.json()

    if res.text == 'Not Found':
        return "Kendo not found"
    return "Kendo bad request"

def data_enrichment_function(contact, session):
    contact_info = contact.contact_info
    li_profile_url = contact_info['ulinc']['li_profile_url']
    li_profile_id = get_li_profile_id(li_profile_url)
    kendo_person = get_kendo_person(li_profile_id)
    if kendo_person == 'Kendo not found':
        new_action = Action(str(uuid4()), contact.contact_id, 22, datetime.utcnow(), json.dumps(kendo_person))
        session.add(new_action)
        session.commit()
        return "Kendo not found"
    elif kendo_person == 'Kendo bad request':
        return "Kendo bad request"
    else:
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
        contact_info['kendo'] = kendo_person
        contact.contact_info = contact_info
        flag_modified(contact, 'contact_info')
        new_action = Action(str(uuid4()), contact.contact_id, 22, datetime.utcnow(), json.dumps(kendo_person))
        session.add(new_action)
        session.commit()
        return "Kendo found"

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if contact := session.query(Contact).filter(Contact.contact_id == json_body['contact_id']).first():
            data_enrichment_function_res = data_enrichment_function(contact, session)
            if data_enrichment_function_res == 'Kendo found':
                print("Kendo found for contact {}".format(contact.contact_id))
                return Response('Kendo found', 200)
            elif data_enrichment_function_res == 'Kendo not found':
                print("Kendo not found for contact {}".format(contact.contact_id))
                return Response('Kendo not found', 200)
            elif data_enrichment_function_res == 'Kendo bad request':
                print("Kendo bad request for contact {}".format(contact.contact_id))
                return Response('Kendo bad request', 200)
            return Response('Unknown error or kendo status for contact {}'.format(contact.contact_id))
        return Response('Unknown contact_id', 200)


if __name__ == '__main__':
    data = {
        'contact_id': '0093d012-c5a7-48ca-92e8-2aca71c9f0ed'
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
