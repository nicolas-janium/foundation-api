# -*- coding: utf-8 -*-

import csv
import io
import logging
from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import Levenshtein as lev
import requests
from flask import Response
from nameparser import HumanName
from sqlalchemy.orm import defer, undefer
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql.expression import and_
from urllib3.exceptions import InsecureRequestWarning

import demoji_module as demoji
from model import (Action, Contact, Contact_source, Ulinc_campaign,
                   Ulinc_campaign_origin_message, Ulinc_config,
                   create_gcf_db_engine, create_gcf_db_session)

# demoji.download_codes()

logger = logging.getLogger('process_contact_sources')
formatter = logging.Formatter('%(levelname)s - %(message)s')
logHandler = logging.StreamHandler()
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

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

def create_new_contact(contact_info, existing_ulinc_campaign_id, contact_source_id, ulinc_client_id=None):
    data = {**base_contact_dict, **contact_info}
    if ulinc_client_id:
        conv = lambda i : i or None
        name = scrub_name(data['Name'])
        return Contact(
            str(uuid4()),
            contact_source_id,
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
            None
        )
    else:
        return Contact(
            str(uuid4()),
            contact_source_id,
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
            None
        )

def process_webhook(ulinc_config, contact_source, session):
    for item in contact_source.contact_source_json:
        existing_contact = session.query(Contact).filter(Contact.ulinc_id == str(item['id'])).first() # if contact exists in the contact table
        existing_ulinc_campaign = session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_config_id == ulinc_config.ulinc_config_id).filter(Ulinc_campaign.ulinc_ulinc_campaign_id == str(item['campaign_id'])).first()
        if contact_source.contact_source_type_id == 1:
            if existing_contact: # if contact exists in the contact table
                # Update contat information. CSV has lets info than webhook responses
                existing_contact_info = existing_contact.contact_info
                new_contact_info = {**base_contact_dict, **item}
                existing_contact_info['ulinc']['email'] = new_contact_info['email']
                existing_contact_info['ulinc']['phone'] = new_contact_info['phone']
                existing_contact_info['ulinc']['website'] = new_contact_info['website']
                existing_contact_info['ulinc']['li_profile_url'] = new_contact_info['profile']
                existing_contact.contact_info = existing_contact_info
                flag_modified(existing_contact, 'contact_info')
                session.commit()

                if existing_cnxn_action := existing_contact.actions.filter(Action.action_type_id == 1).first():
                    pass
                else:
                    connection_action = Action(str(uuid4()), existing_contact.contact_id, 1, datetime.utcnow(), None, None)
                    session.add(connection_action)
            else:
                new_contact = create_new_contact(
                    item,
                    existing_ulinc_campaign.ulinc_campaign_id if existing_ulinc_campaign else Ulinc_campaign.unassigned_ulinc_campaign_id,
                    contact_source.contact_source_id
                )
                connection_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow(), None, None)
                session.add(new_contact)
                session.add(connection_action)
        elif contact_source.contact_source_type_id == 2:
            if existing_contact:
                # Update contat information. CSV has lets info than webhook responses
                contact_id = existing_contact.contact_id
                existing_contact_info = existing_contact.contact_info
                new_contact_info = {**base_contact_dict, **item}
                existing_contact_info['ulinc']['email'] = new_contact_info['email']
                existing_contact_info['ulinc']['phone'] = new_contact_info['phone']
                existing_contact_info['ulinc']['website'] = new_contact_info['website']
                existing_contact_info['ulinc']['li_profile_url'] = new_contact_info['profile']
                existing_contact.contact_info = existing_contact_info
                flag_modified(existing_contact, 'contact_info')
                session.commit()
            else:
                new_contact = create_new_contact(
                    item,
                    existing_ulinc_campaign.ulinc_campaign_id if existing_ulinc_campaign else Ulinc_campaign.unassigned_ulinc_campaign_id,
                    contact_source.contact_source_id
                )
                session.add(new_contact)
                contact_id = new_contact.contact_id
            new_message_action = Action(
                str(uuid4()),
                contact_id,
                2,
                datetime.utcnow(),
                str(item['message']),
                None
            )
            session.add(new_message_action)
        elif contact_source.contact_source_type_id == 3:
            if existing_contact:
                # Update contat information. CSV has less info than webhook responses
                contact_id = existing_contact.contact_id
                existing_contact_info = existing_contact.contact_info
                new_contact_info = {**base_contact_dict, **item}
                existing_contact_info['ulinc']['email'] = new_contact_info['email']
                existing_contact_info['ulinc']['phone'] = new_contact_info['phone']
                existing_contact_info['ulinc']['website'] = new_contact_info['website']
                existing_contact_info['ulinc']['li_profile_url'] = new_contact_info['profile']
                existing_contact.contact_info = existing_contact_info
                flag_modified(existing_contact, 'contact_info')
                session.commit()

            else:
                new_contact = create_new_contact(
                    item,
                    existing_ulinc_campaign.ulinc_campaign_id if existing_ulinc_campaign else Ulinc_campaign.unassigned_ulinc_campaign_id,
                    contact_source.contact_source_id
                )
                session.add(new_contact)
                contact_id = new_contact.contact_id

            ### If message item is origin message, handle accordingly ###
            is_c_origin = False
            is_m_origin = False
            item_message = str(item['message']).strip().replace('\r', '').replace('\n', '')
            if existing_ulinc_campaign:
                for origin_message in session.query(Ulinc_campaign_origin_message).filter(Ulinc_campaign_origin_message.ulinc_campaign_id == existing_ulinc_campaign.ulinc_campaign_id).all():
                    origin_message = str(origin_message.message).strip().replace('\r', '').replace('\n', '')
                    if lev.ratio(origin_message, item_message) > 0.8:
                        if existing_ulinc_campaign.ulinc_is_messenger:
                            is_m_origin = True
                            break
                        else:
                            is_c_origin = True
                            break

            new_action = Action(
                str(uuid4()),
                contact_id,
                13 if is_m_origin else 23 if is_c_origin else 3,
                datetime.utcnow(),
                str(item['message']),
                None
            )
            session.add(new_action)
        else:
            print('Unknown webhook response type')
        session.commit()

def process_csv(ulinc_config, ulinc_campaign, contact_source, session):
    for item in contact_source.contact_source_json:
        existing_contact = session.query(Contact).filter(Contact.ulinc_id == str(ulinc_config.ulinc_client_id + item['Contact ID'])).first()
        if item['Status'] == 'In Queue':
            if existing_contact:
                if existing_action := existing_contact.actions.filter(Action.action_type_id == 18).first():
                    continue
                else:
                    new_action = Action(str(uuid4()), existing_contact.contact_id, 18, datetime.utcnow(), None)
                    session.add(new_action)
            else:
                new_contact = create_new_contact(
                    item, ulinc_campaign.ulinc_campaign_id, contact_source.contact_source_id, ulinc_client_id=ulinc_config.ulinc_client_id
                )
                session.add(new_contact)
                new_action = Action(str(uuid4()), new_contact.contact_id, 18, datetime.utcnow(), None)
                session.add(new_action)
        elif item['Status'] == 'Connect Req':
            if existing_contact:
                if existing_action := existing_contact.actions.filter(Action.action_type_id == 19).first():
                    continue
                else:
                    existing_contact_info = existing_contact.contact_info
                    existing_contact_info['li_profile_url'] = item['LinkedIn profile']
                    existing_contact.contact_info = existing_contact_info
                    new_action = Action(str(uuid4()), existing_contact.contact_id, 19, datetime.utcnow(), None)
                    session.add(new_action)
            else:
                new_contact = create_new_contact(
                    item, ulinc_campaign.ulinc_campaign_id, contact_source.contact_source_id, ulinc_client_id=ulinc_config.ulinc_client_id
                )
                session.add(new_contact)
                new_action = Action(str(uuid4()), new_contact.contact_id, 19, datetime.utcnow(), None)
                session.add(new_action)
        elif item['Status'] == 'Connect Error':
            if existing_contact:
                if existing_action := existing_contact.actions.filter(Action.action_type_id == 20).first():
                    continue
                else:
                    new_action = Action(str(uuid4()), existing_contact.contact_id, 20, datetime.utcnow(), None)
                    session.add(new_action)
            else:
                new_contact = create_new_contact(
                    item, ulinc_campaign.ulinc_campaign_id, contact_source.contact_source_id, ulinc_client_id=ulinc_config.ulinc_client_id
                )
                session.add(new_contact)
                new_action = Action(str(uuid4()), new_contact.contact_id, 20, datetime.utcnow(), None)
                session.add(new_action)
        elif item['Status'] == 'Later':
            if existing_contact:
                if existing_action := existing_contact.actions.filter(Action.action_type_id == 21).first():
                    continue
                else:
                    new_action = Action(str(uuid4()), existing_contact.contact_id, 21, datetime.utcnow(), None)
                    session.add(new_action)
            else:
                new_contact = create_new_contact(
                    item, ulinc_campaign.ulinc_campaign_id, contact_source.contact_source_id, ulinc_client_id=ulinc_config.ulinc_client_id
                )
                session.add(new_contact)
                new_action = Action(str(uuid4()), new_contact.contact_id, 21, datetime.utcnow(), None)
                session.add(new_action)
        elif item['Status'] == 'No Interest':
            if existing_contact:
                if existing_action := existing_contact.actions.filter(Action.action_type_id == 11).first():
                    continue
                else:
                    new_action = Action(str(uuid4()), existing_contact.contact_id, 11, datetime.utcnow(), None)
                    session.add(new_action)
            else:
                new_contact = create_new_contact(
                    item, ulinc_campaign.ulinc_campaign_id, contact_source.contact_source_id, ulinc_client_id=ulinc_config.ulinc_client_id
                )
                session.add(new_contact)
                new_action = Action(str(uuid4()), new_contact.contact_id, 11, datetime.utcnow(), None)
                session.add(new_action)
        elif item['Status'] == 'Connected':
            if existing_contact:
                if existing_cnxn_action := existing_contact.actions.filter(Action.action_type_id.in_([1])).first():
                    if stop_campaign_actions := existing_contact.actions.filter(Action.action_type_id.in_([2, 6, 11, 21])).order_by(Action.action_timestamp.desc()).all():
                        if continue_campaign_action := existing_contact.actions.filter(Action.action_type_id == 14).order_by(Action.action_timestamp.desc()).first():
                            if stop_campaign_actions[0].action_timestamp > continue_campaign_action.action_timestamp:
                                new_action = Action(str(uuid4()), existing_contact.contact_id, 14, datetime.utcnow(), None)
                                session.add(new_action)
                            else:
                                continue
                        else:
                            new_action = Action(str(uuid4()), existing_contact.contact_id, 14, datetime.utcnow(), None)
                            session.add(new_action)
                    else:
                        continue
                else:
                    new_action = Action(str(uuid4()), existing_contact.contact_id, 1, datetime.utcnow(), None)
                    session.add(new_action)
            else:
                new_contact = create_new_contact(
                    item, ulinc_campaign.ulinc_campaign_id, contact_source.contact_source_id, ulinc_client_id=ulinc_config.ulinc_client_id
                )
                session.add(new_contact)
                new_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow(), None)
                session.add(new_action)
        elif item['Status'] == 'Replied':
            if existing_contact:
                if existing_cnxn_action := existing_contact.actions.filter(Action.action_type_id == 1).first():
                    pass
                else:
                    cnxn_action = Action(str(uuid4()), existing_contact.contact_id, 1, datetime.utcnow(), None)
                    session.add(cnxn_action)
            else:
                new_contact = create_new_contact(
                    item, ulinc_campaign.ulinc_campaign_id, contact_source.contact_source_id, ulinc_client_id=ulinc_config.ulinc_client_id
                )
                session.add(new_contact)
                new_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow(), None)
                session.add(new_action)
        elif item['Status'] == 'Talking':
            if existing_contact:
                if existing_cnxn_action := existing_contact.actions.filter(Action.action_type_id == 1).first():
                    pass
                else:
                    cnxn_action = Action(str(uuid4()), existing_contact.contact_id, 1, datetime.utcnow(), None)
                    session.add(cnxn_action)
            else:
                new_contact = create_new_contact(
                    item, ulinc_campaign.ulinc_campaign_id, contact_source.contact_source_id, ulinc_client_id=ulinc_config.ulinc_client_id
                )
                session.add(new_contact)
                new_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow(), None)
                session.add(new_action)
    session.commit()

def process_contact_source_function(ulinc_config, contact_source, session):
    if contact_source.contact_source_type_id != 4:
        try:
            process_webhook(ulinc_config, contact_source, session)
            contact_source.is_processed = True
            session.commit()
            return True
        except Exception as err:
            logger.error("Error while processing contact source {}: {}".format(contact_source.contact_source_id, err))
            return None
    else:
        ulinc_ulinc_campaign_id = contact_source.contact_source_json[0]['Campaign ID']
        ulinc_campaign = session.query(Ulinc_campaign).filter(and_(Ulinc_campaign.ulinc_ulinc_campaign_id == ulinc_ulinc_campaign_id, Ulinc_campaign.ulinc_config_id == ulinc_config.ulinc_config_id)).first()
        try:
            process_csv(ulinc_config, ulinc_campaign, contact_source, session)
            contact_source.is_processed = True
            session.commit()
            return True
        except Exception as err:
            logger.error("Error while process contact source {}: {}".format(contact_source.contact_source_id, err))
            return None

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if ulinc_config := session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first():
            if ulinc_config.is_working:
                if contact_source := session.query(Contact_source).filter(Contact_source.contact_source_id == json_body['contact_source_id']).options(defer('contact_source_json')).first():
                    if not contact_source.is_processed:
                        if process_contact_source_function(ulinc_config, contact_source, session):
                            return Response("Success", 200) # Task should not repeat
                        return Response("Unknown Error", 200) # Task should not repeat
                    return Response("Contact_source already processed")
                return Response("Unknown contact_source_id", 200) # Task should not repeat
            return Response("Ulinc_config not working", 200) # Task should not repeat
        return Response("Unknown ulinc_config_id", 200) # Task should not repeat


if __name__ == '__main__':
    data = {
        "ulinc_config_id": "d0b9f557-942c-4d5f-b986-8ff935ebce81",
        "contact_source_id": "e6fcfe00-d61b-4f55-b946-f76db032c7a7"
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
