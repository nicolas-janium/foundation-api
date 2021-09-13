import os
from datetime import datetime, timedelta
from email.header import Header
from email.message import EmailMessage
from unittest.mock import Mock
from uuid import uuid4
import json
from pprint import pprint

import boto3
import minify_html
import requests
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup as Soup
from flask import Response, escape
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from urllib3.exceptions import InsecureRequestWarning

from model import (Action, Contact, Contact_source, Email_config,
                   Janium_campaign, Janium_campaign_step,
                   create_gcf_db_engine, create_gcf_db_session)

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning) # pylint: disable=no-member


def poll_and_save_webhook(ulinc_config, wh_url, wh_type, session):
    res = requests.get(wh_url, verify=False)
    if res.ok:
        if res_json := res.json():
            contact_source = Contact_source(str(uuid4()), ulinc_config.ulinc_config_id, wh_type, res_json)
            session.add(contact_source)
            session.commit()
            return "Webhook response saved"
        return "Webhook response empty"
    return "Bad request"

def create_reply_thread(janium_campaign, janium_campaign_step, contact, from_entity, session):
    email_html = janium_campaign_step.janium_campaign_step_body
    main_soup = Soup(email_html, 'html.parser')
    main_soup_html_tag = main_soup.find('html')
    main_soup_div_tag = main_soup.find('div')

    # prev_step_ids = [
    #     step.janium_campaign_step_id for step in janium_campaign.janium_campaign_steps\
    #                                                             .filter(Janium_campaign_step.janium_campaign_step_delay < janium_campaign_step.janium_campaign_step_delay)\
    #                                                             .order_by(Janium_campaign_step.janium_campaign_step_delay.asc())\
    #                                                             .all()
    # ]
    # prev_email_actions = session.query(Action).filter(Action.contact_id == contact.contact_id)\
    #                                           .filter(Action.janium_campaign_step_id.in_(prev_step_ids))\
    #                                           .order_by(Action.action_timestamp.desc())\
    #                                           .all()
    
    if prev_janium_campaign_step := session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_id == janium_campaign_step.janium_campaign_id)\
                                                                       .filter(Janium_campaign_step.janium_campaign_step_type_id == janium_campaign_step.janium_campaign_step_type_id)\
                                                                       .filter(Janium_campaign_step.janium_campaign_step_delay < janium_campaign_step.janium_campaign_step_delay)\
                                                                       .order_by(Janium_campaign_step.janium_campaign_step_delay.desc())\
                                                                       .first():
        if prev_email_action := session.query(Action).filter(Action.contact_id == contact.contact_id).filter(Action.janium_campaign_step_id == prev_janium_campaign_step.janium_campaign_step_id).first():
            soup = Soup(prev_email_action.action_message, 'html.parser')
            prev_action_div_tag = soup.find('div') # Main big div
            prev_action_message_div_tag = prev_action_div_tag.find('div') # div tag containing the actual message text
            reply_div_tag = soup.new_tag('div') # New div to be made 

            reply_header = """\
                <div>\
                    <p>\
                        <b>From:</b> {}<br>\
                        <b>Date:</b> {}<br>\
                        <b>To:</b> {}<br>\
                        <b>Subject:</b> Re:{}\
                    </p>\
                </div>\
            """.format(
                escape(from_entity),
                prev_email_action.action_timestamp.strftime(r'%A, %B %d, %Y at %I:%M %p'),
                escape('Nicolas Arnold <nic@janium.io>'),
                janium_campaign_step.janium_campaign_step_subject
            ).strip()
            reply_header_div_tag = Soup(reply_header, 'html.parser')

            reply_div_tag.insert(0, prev_action_div_tag)
            reply_div_tag.insert(0, reply_header_div_tag)
            
            main_soup_html_tag.insert(1000, reply_div_tag)
    # return str(main_soup.prettify(formatter=None))
    return main_soup



def add_preview_text(email_html, details):
    soup = Soup(email_html, 'html.parser')
    body_tag = soup.find('body')

    prev_text_div_tag = soup.new_tag('div', attrs={'style': 'display: none; max-height: 0px; overflow: hidden;'})
    prev_text_div_tag.string = details['preview_text']

    white_space_div_tag = soup.new_tag('div', attrs={'style': 'display: none; max-height: 0px; overflow: hidden;'})
    white_space_div_string = r'&nbsp;&zwnj;'
    for i in range(200):
        white_space_div_string += r'&nbsp;&zwnj;'
    white_space_div_tag.string = white_space_div_string

    body_tag.insert(0, white_space_div_tag)
    body_tag.insert(0, prev_text_div_tag)
    return str(soup.prettify(formatter=None))

def insert_key_words(email_html, key_words_dict):
    email_html = str(email_html)
    for key in key_words_dict:
        key_string = str('{' + key + '}')
        if key_string in email_html:
            email_html = email_html.replace(key_string, key_words_dict[key])
    return email_html

def add_janium_email_identifier(email_html):
    soup = Soup(email_html, 'html.parser')
    html_tag = soup.find('html')
    div = soup.new_tag('div', attrs={'style': 'opacity:0'})
    div.string = os.getenv('JANIUM_EMAIL_ID')
    html_tag.insert(1000, div)
    return str(soup.prettify(formatter=None))

def send_email_with_ses(email_config, janium_campaign, janium_campaign_step, contact, session):
    action_id = str(uuid4())
    main_email = EmailMessage()
    main_email.make_alternative()

    key_words_dict = contact.create_key_words_dict()

    email_subject = janium_campaign_step.janium_campaign_step_subject
    email_subject = insert_key_words(email_html=email_subject, key_words_dict=key_words_dict)

    main_email['Subject'] = email_subject
    main_email['From'] = str(Header('{} <{}>')).format(email_config.from_full_name, email_config.from_address)

    main_email['To'] = contact.get_emails()[0]
    main_email.add_header('j_a_id', action_id)
    main_email.add_header('j_e_id', os.getenv('JANIUM_EMAIL_ID'))
    main_email['MIME-Version'] = '1.0'

    if janium_campaign.is_reply_in_email_thread:
        email_html = create_reply_thread(janium_campaign, janium_campaign_step, contact)
    else:
        email_html = janium_campaign_step.janium_campaign_step_body
    
    # email_html = add_preview_text(email_html, details)
    email_html = add_janium_email_identifier(email_html)
    email_html = insert_key_words(email_html=email_html, key_words_dict=key_words_dict)

    # main_email.add_alternative(html2text(email_html), 'plain')
    main_email.add_alternative(email_html, 'html')

    client = boto3.client(
        'ses',
        region_name="us-east-2",
        aws_access_key_id=os.getenv('SES_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('SES_SECRET_ACCESS_KEY')
    )
    try:
        response = client.send_raw_email(
            Source=main_email['From'],
            Destinations=[main_email['To']],
            RawMessage={
                "Data": main_email.as_string()
            }
        )
        action = Action(
            action_id,
            contact.contact_id,
            4,
            datetime.utcnow(),
            minify_html.minify(email_html, minify_js=False),
            to_email_addr=contact.get_emails()[0],
            email_message_id=response['MessageId'],
            janium_campaign_step_id=janium_campaign_step.janium_campaign_step_id
        )
        session.add(action)
        session.commit()
        return True
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
        return None

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if email_config := session.query(Email_config).filter(Email_config.email_config_id == json_body['email_config_id']).first():
            if janium_campaign := session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == json_body['janium_campaign_id']).first():
                if janium_campaign_step := session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == json_body['janium_campaign_step_id']).first():
                    if contact := session.query(Contact).filter(Contact.contact_id == json_body['contact_id']).first():
                        return create_reply_thread(janium_campaign, janium_campaign_step, contact, 'Nic Arnold <nic@janium.io>', session)
                        # if contact.is_messaging_task_valid():
                        #     ulinc_config = janium_campaign.janium_campaign_ulinc_config
                        #     webhook_response = poll_and_save_webhook(ulinc_config, ulinc_config.new_message_webhook, 2, session)
                        #     if webhook_response == 'Webhook response saved':
                        #         gct_client = tasks_v2.CloudTasksClient()
                        #         gct_parent = gct_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send-email')
                        #         payload = json_body
                        #         task = {
                        #             "http_request": {  # Specify the type of request.
                        #                 "http_method": tasks_v2.HttpMethod.POST,
                        #                 "url": os.getenv('SEND_EMAIL_TRIGGER_URL'),
                        #                 'body': json.dumps(payload).encode(),
                        #                 'headers': {
                        #                     'Content-type': 'application/json'
                        #                 }
                        #             }
                        #         }

                        #         # Add the timestamp to the tasks.
                        #         timestamp = timestamp_pb2.Timestamp()
                        #         timestamp.FromDatetime(datetime.utcnow() + timedelta(minutes=15))
                        #         task['schedule_time'] = timestamp

                        #         task_response = gct_client.create_task(parent=gct_parent, task=task)
                        #         return Response('New message webhook response was not empty. Created new task', 200)
                        #     elif webhook_response == 'Webhook response empty':
                        #         if send_email_with_ses(email_config, janium_campaign, janium_campaign_step, contact, session):
                        #             return Response('Success', 200)
                        #         return Response('IDK', 200)
                        #     return Response('IDK', 200)
                        # return Response("Messaging task no longer valid", 200)
                    return Response("Unknown contact_id", 200)
                return Response("Unknown janium_campaign_id", 200)
        return Response("Failure. Email config does not exist", 200) # Should not repeat


if __name__ == '__main__':
    data = {
        "janium_campaign_id": "5598484a-2923-403f-bfdd-5a1e354792c7",
        "email_config_id":  "ab59f3e9-0719-4858-9bff-a5548ceaca86", # nic@janium.io
        "janium_campaign_step_id": "163158a4-d3e9-4cae-b27d-775967a2d03f",
        "ulinc_campaign_id": "753d27be-c5e5-4b12-806d-b9bf60ccab5f",
        "contact_id": "0093d012-c5a7-48ca-92e8-2aca71c9f0ed"
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    # print(func_res.get_data())
    pprint(func_res)
    # print(func_res.status_code)

    # key_words_dict = {
    #     "FirstName": "Tim",
    #     "Location": "SF",
    #     "Company": "Google"
    # }
    # email_html = r"<html>Hello, {FirstName}, how is it in {Location} at {Company}?</html>"

    # email_html = insert_key_words(email_html=email_html, key_words_dict=key_words_dict)
    # print(email_html)
