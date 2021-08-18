import base64
import json
import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.header import Header
from email.message import EmailMessage
from email.utils import make_msgid
from uuid import uuid4
import pytz
import math

import requests
from bs4 import BeautifulSoup as Soup
import boto3
import google.auth
from google.cloud import secretmanager
from google.oauth2 import service_account
from botocore.exceptions import ClientError
from html2text import html2text
from workdays import networkdays
from foundation_api.V1.sa_db.model import *

logger = logging.getLogger('send_email_task')
formatter = logging.Formatter('%(levelname)s - %(message)s')
logHandler = logging.StreamHandler()
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

PROJECT_ID = os.getenv('PROJECT_ID')    

def get_sendgrid_key():
    if os.getenv('IS_CLOUD') == 'True':
        creds, project = google.auth.default()
    else:
        creds = service_account.Credentials.from_service_account_file('/home/nicolas/gcp/key.json')
    client = secretmanager.SecretManagerServiceClient(credentials=creds)
    secret_name = "sendgrid-api-key"
    project_id = "janium0-0"
    request = {"name": f"projects/{project_id}/secrets/{secret_name}/versions/latest"}
    response = client.access_secret_version(request)
    return response.payload.data.decode('UTF-8')

def get_sendgrid_headers():
    headers = {
        "authorization": "Bearer {}".format(os.getenv('SENDGRID_API_KEY'))
    }
    return headers

def get_sendgrid_sender(sender_id):
    url = "https://api.sendgrid.com/v3/verified_senders"

    res = requests.request("GET", url, headers=get_sendgrid_headers())
    if res.ok:
        res_json = res.json()
        # pprint(res_json)
        if senders := res_json['results']:
            for sender in senders:
                if str(sender['id']) == sender_id:
                    return sender
        else:
            logger.warning("Get sender returned an empty array")
            return None
    else:
        logger.error(str("Request to get sender failed. {}".format(res.text)))
        return None

def add_identifier(email_html):
    soup = Soup(email_html, 'html.parser')
    html_tag = soup.find('html')
    div = soup.new_tag('div', attrs={'style': 'opacity:0'})
    div.string = os.getenv('JANIUM_EMAIL_ID')
    html_tag.insert(1000, div)
    return str(soup)

def add_footer(email_html, contact_id, contact_email):
    opt_out_url = "https://us-central1-{}.cloudfunctions.net/email-opt-out-function".format(PROJECT_ID)
    opt_out_url += "?contact_id={}&landing=1&contact_email={}".format(contact_id, contact_email)
    soup = Soup(email_html, 'html.parser')
    div = soup.new_tag('div')
    email_preferences = r"""
        <p style="text-align: left;font-size: 10px;">Received this email by mistake? Click <a href="{opt_out_url}">here</a>.
        </p>
        """
    p_soup = Soup(email_preferences, 'html.parser')
    div.append(p_soup)
    soup.append(div)

    return str(soup).replace(r'{opt_out_url}', opt_out_url)

def send_email_with_sendgrid(details):
    url = "https://api.sendgrid.com/v3/mail/send"

    action_id = str(uuid4())
    # api_key = get_sendgrid_key()
    sender = get_sendgrid_sender(details['sendgrid_sender_id'])
    from_email = sender['from_email']

    # message = add_footer(details['email_body'], details['contact_id'], details['contact_email'])
    message = details['email_body']
    message = add_identifier(message)
    message_id = make_msgid(idstring=os.getenv('JANIUM_EMAIL_ID'), domain=from_email[from_email.index('@') + 1 : ])

    if sender:
        payload = {
            "personalizations": [
                {
                    "to": [
                        {
                            "email": details['contact_email'],
                            "name": details['contact_first_name']
                        }
                    ],
                    "subject": details['email_subject']
                }
            ],
            "from": {
                "email": sender['from_email'],
                "name": sender['from_name']
            },
            "reply_to": {
                "email": sender['reply_to'],
                "name": sender['reply_to_name']
            },
            "content": [
                {
                    "type": "text/plain",
                    "value": html2text(message)
                },
                {
                    "type": "text/html",
                    "value": message
                }
            ],
            "headers": {"j_a_id": action_id, "Message-ID": message_id, "j_c_id": details['janium_campaign_id']}, # Janium Action Id and Janium Campaign Id
            "tracking_settings": {
                "click_tracking": {
                    "enable": False,
                    "enable_text": False
                },
                "open_tracking": {
                    "enable": False
                }
            }
        }
    else:
        logger.warning("Sender is empty")
        return None
    try:
        res = requests.post(url=url, json=payload, headers=get_sendgrid_headers())
        if res.ok:
            action = Action(action_id, details["contact_id"], 4, datetime.utcnow(), message, to_email_addr=details['contact_email'], email_message_id=message_id)
            db.session.add(action)
            db.session.commit()
            return details['contact_email']
    except Exception as err:
        logger.error(str("There was an error while sending an email to {} for account {}. Error: {}".format(details['contact_email'], sender['from_name'], err)))
        return None

def send_email_with_ses(details, from_address, from_full_name, session):
    from foundation_api.V1.utils.test import body
    action_id = str(uuid4())
    main_email = EmailMessage()
    main_email.make_alternative()

    main_email['Subject'] = details['email_subject']
    # main_email['Subject'] = "Amazon SES Test (SDK for Python)"
    # main_email['From'] = str(Header('{} <{}>')).format('Nic Arnold', 'nic@janium.io')
    main_email['From'] = str(Header('{} <{}>')).format(from_full_name, from_address)

    # main_email['To'] = 'nic@janium.io'
    main_email['To'] = details['contact_email']
    # main_email['To'] = 'bounce@simulator.amazonses.com'
    # main_email['To'] = 'complaint@simulator.amazonses.com'
    main_email.add_header('j_a_id', action_id)
    main_email['MIME-Version'] = '1.0'

    # email_html = details['email_body']
    # email_html = email_html.replace(r"{FirstName}", details['contact_first_name'])
    # email_html = add_identifier(email_html)
    email_html = details['email_body']
    # email_html = add_identifier(email_html)

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
        action = Action(action_id, details['contact_id'], 4, datetime.utcnow(), email_html, to_email_addr=details['contact_email'])
        session.add(action)
        session.commit()
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
        return None


def send_email_with_smtp(details):
    username, password = details['email_creds']

    recipient = details['contact_email']

    contact_id = details['contact_id']
    action_id = str(uuid4())

    main_email = EmailMessage()
    main_email.make_alternative()


    main_email['Subject'] = details['email_subject']
    main_email['From'] = str(Header('{} <{}>')).format(details['from_full_name'], username)
    main_email['To'] = recipient
    main_email['Message-ID'] = make_msgid(idstring=os.getenv('JANIUM_EMAIL_ID'), domain=username[username.index('@') + 1 : ])
    main_email.add_header('j_a_id', action_id) 
    main_email['MIME-Version'] = '1.0'

    # email_html = add_tracker(details['email_body'], contactid, messageid)
    # email_html = add_footer(details['email_body'], contact_id, details['contact_email'])
    email_html = details['email_body']
    email_html = email_html.replace(r"{FirstName}", details['contact_first_name'])
    email_html = add_identifier(email_html)

    main_email.add_alternative(html2text(email_html), 'plain')
    main_email.add_alternative(email_html, 'html')


    with smtplib.SMTP(details['smtp_address'], 587) as server:
        server.ehlo()
        server.starttls()
        # username = '123'
        server.login(username, password)
        server.send_message(main_email)
        print("Sent an email to {}".format(details['contact_id']))

    action = Action(action_id, contact_id, 4, datetime.utcnow(), email_html, to_email_addr=recipient)
    db.session.add(action)
    db.session.commit()
    return details['contact_email']

# def get_email_targets(janium_campaign, is_sendgrid):
#     steps = janium_campaign.janium_campaign_steps.filter(Janium_campaign_step.janium_campaign_step_type_id != 4).order_by(Janium_campaign_step.janium_campaign_step_delay).all()

#     ### Only get contacts who have not been email blacklisted or who have bounced email actions ###
#     contacts = [ 
#         contact
#         for contact 
#         in janium_campaign.contacts
#         if not contact.actions.filter(Action.action_type_id.in_([7,15])).first() and len(contact.get_emails()) > 0
#     ]

#     email_targets_list = []
#     for contact in contacts:
#         if previous_received_messages := contact.actions.filter(Action.action_type_id.in_([2, 6, 11, 21])).order_by(Action.action_timestamp.desc()).all():
#             if continue_campaign_action := contact.actions.filter(Action.action_type_id == 14).order_by(Action.action_timestamp.desc()).first():
#                 if previous_received_messages[0].action_timestamp > continue_campaign_action.action_timestamp:
#                     continue
#             else:
#                 continue

#         if cnxn_action := contact.actions.filter(Action.action_type_id == 1).order_by(Action.action_timestamp.desc()).first():
#             prev_actions = contact.actions.filter(Action.action_type_id.in_([3,4])).filter(Action.action_timestamp >= cnxn_action.action_timestamp).order_by(Action.action_timestamp.desc()).all()
#             sent_emails = [sent_email for sent_email in prev_actions if prev_actions and sent_email.janium_campaign_step_type_id == 4]
#             num_sent_emails = len(sent_emails) if sent_emails else 0
#             last_sent_email = sent_emails[0] if sent_emails else None

#             if continue_campaign_action := contact.actions.filter(Action.action_type_id == 14).order_by(Action.action_timestamp.desc()).first():
#                 cnxn_timestamp = cnxn_action.action_timestamp
#                 if last_sent_email:
#                     days_to_add = networkdays(last_sent_email.action_timestamp, continue_campaign_action.action_timestamp) - 1
#                 else:
#                     days_to_add = networkdays(previous_received_messages[0].action_timestamp, continue_campaign_action.action_timestamp) - 1
#                 while days_to_add > 0:
#                     cnxn_timestamp += timedelta(days=1)
#                     if cnxn_timestamp.weekday() >= 5: # sunday = 6
#                         continue
#                     days_to_add -= 1
#             else:
#                 cnxn_timestamp = cnxn_action.action_timestamp

#             day_diff = networkdays(cnxn_timestamp, datetime.utcnow()) - 1

#             for i, step in enumerate(steps):
#                 if step.janium_campaign_step_type_id == 2:
#                     add_contact = False
#                     body = step.janium_campaign_step_body
#                     subject = step.janium_campaign_step_subject
#                     if step.janium_campaign_step_delay <= day_diff:
#                         if num_sent_emails < i + 1:
#                             if i == 0:
#                                 add_contact = True
#                                 break
#                             else:
#                                 if (networkdays(prev_actions[0].action_timestamp, datetime.utcnow()) - 1) >= (step.janium_campaign_step_delay - steps[i-1].janium_campaign_step_delay):
#                                     add_contact = True
#                                     break
#                                 else:
#                                     continue
#                         else:
#                             continue
#                     else:
#                         continue
#                 else:
#                     continue
#         # Pre connection email targets made possible by data enrichment
#         elif cnxn_req_action := contact.actions.filter(Action.action_type_id == 19).order_by(Action.action_timestamp.desc()).first():
#             prev_actions = contact.actions.filter(Action.action_type_id.in_([3,4])).filter(Action.action_timestamp >= cnxn_req_action.action_timestamp).order_by(Action.action_timestamp.desc()).all()
#             sent_emails = [sent_email for sent_email in prev_actions if prev_actions and sent_email.janium_campaign_step_type_id == 4]
#             num_sent_emails = len(sent_emails) if sent_emails else 0
#             last_sent_email = sent_emails[0] if sent_emails else None

#             if len(contact.get_emails()):
#                 cnxn_req_timestamp = cnxn_req_action.action_timestamp
#                 day_diff = networkdays(cnxn_req_timestamp, datetime.utcnow()) - 1
                
#                 steps = janium_campaign.janium_campaign_steps.filter(Janium_campaign_step.janium_campaign_step_type_id == 4).order_by(Janium_campaign_step.janium_campaign_step_delay).all()
#                 for i, step in enumerate(steps):
#                     add_contact = False
#                     body = step.janium_campaign_step_body
#                     subject = step.janium_campaign_step_subject
#                     if step.janium_campaign_step_delay <= day_diff:
#                         if num_sent_emails < i + 1:
#                             if i == 0:
#                                 add_contact = True
#                                 break
#                             else:
#                                 if (networkdays(prev_actions[0].action_timestamp, datetime.utcnow()) - 1) >= (step.janium_campaign_step_delay - steps[i-1].janium_campaign_step_delay):
#                                     add_contact = True
#                                     break
#                                 else:
#                                     continue
#                         else:
#                             continue
#                     else:
#                         continue
#         if add_contact:
#             email_targets_list.append(
#                 {
#                     "is_sendgrid": is_sendgrid,
#                     "sendgrid_sender_id": janium_campaign.email_config.sendgrid_sender_id if is_sendgrid else None,
#                     "from_full_name": janium_campaign.email_config.from_full_name,
#                     "smtp_address": None if is_sendgrid else janium_campaign.email_config.email_server.smtp_address,
#                     "smtp_port": None if is_sendgrid else janium_campaign.email_config.email_server.smtp_tls_port,
#                     "email_creds": None if is_sendgrid else (janium_campaign.email_config.credentials.username, janium_campaign.email_config.credentials.password),
#                     "janium_campaign_id": janium_campaign.janium_campaign_id,
#                     "contact_id": contact.contact_id,
#                     "contact_first_name": contact.contact_info['ulinc']['first_name'],
#                     "contact_full_name": str(contact.contact_info['ulinc']['first_name'] + ' ' + contact.contact_info['ulinc']['last_name']),
#                     "contact_email": contact.get_emails()[0],
#                     "email_subject": subject,
#                     "email_body": body
#                 }
#             )
#     return email_targets_list

def send_email_function(email_config, email_target_details, session):
    if email_config.is_ses:
        if send_email_with_ses(email_target_details, email_config.from_address, email_config.from_full_name, session):
            return 1
    elif email_config.is_sendgrid:
        pass
    elif email_config.is_smtp:
        pass
    

if __name__ == '__main__':
    payload = {
        "account_id": "7040c021-9986-4b52-a655-d167bc0a4f22"
    }
    payload = json.dumps(payload)
    payload = base64.b64encode(str(payload).encode("utf-8"))
    event = {
        "data": payload
    }
    # main(event, 1)
    # session = get_session()
    # action1 = session.query(Action).filter(Action.action_type_id == 1).first()
    # action2 = session.query(Action).filter(Action.action_type_id == 11).first()

    # print(networkdays(action1.action_timestamp, datetime.now(), holidays=[]))
    # print(networkdays(action1.action_timestamp, action2.action_timestamp, holidays=[]))
    # get_sendgrid_sender('123')

    send_email_with_ses(123)
    # print(123)