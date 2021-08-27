import os
from datetime import datetime
from email.header import Header
from email.message import EmailMessage
from unittest.mock import Mock
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup as Soup
from flask import Response

from model import (Action, Contact, Email_config, create_gcf_db_engine,
                   create_gcf_db_session)


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


def insert_key_words(email_html, details):
    try:
        return str(email_html).replace(r"{FirstName}", details['contact_first_name'])
    except:
        return email_html

def add_janium_email_identifier(email_html):
    soup = Soup(email_html, 'html.parser')
    html_tag = soup.find('html')
    div = soup.new_tag('div', attrs={'style': 'opacity:0'})
    div.string = os.getenv('JANIUM_EMAIL_ID')
    html_tag.insert(1000, div)
    return str(soup.prettify(formatter=None))

def send_email_with_ses(details, from_address, from_full_name, session):
    action_id = str(uuid4())
    main_email = EmailMessage()
    main_email.make_alternative()

    main_email['Subject'] = details['email_subject']
    main_email['From'] = str(Header('{} <{}>')).format(from_full_name, from_address)

    main_email['To'] = details['contact_email']
    main_email.add_header('j_a_id', action_id)
    main_email.add_header('j_e_id', os.getenv('JANIUM_EMAIL_ID'))
    main_email['MIME-Version'] = '1.0'

    email_html = details['email_body']
    # email_html = add_preview_text(email_html, details)
    email_html = add_janium_email_identifier(email_html)
    email_html = insert_key_words(email_html, details)

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
        action = Action(action_id, details['contact_id'], 4, datetime.utcnow(), email_html, to_email_addr=details['contact_email'], email_message_id=response['MessageId'])
        session.add(action)
        session.commit()
        return True
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
        return None

# def send_email_function(email_config, email_target_details, session):
#     if email_config.is_ses:
#         if send_email_with_ses(email_target_details, email_config.from_address, email_config.from_full_name, session):
#             return True
#         return None
#     elif email_config.is_sendgrid:
#         return None
#     elif email_config.is_smtp:
#         return None

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if email_config := session.query(Email_config).filter(Email_config.email_config_id == json_body['email_target_details']['email_config_id']).first():
            if contact := session.query(Contact).filter(Contact.contact_id == json_body['email_target_details']['contact_id']).first():
                if contact.is_messaging_task_valid():
                    if send_email_with_ses(json_body['email_target_details'], email_config.from_address, email_config.from_full_name, session):
                        return Response('Success', 200)
                    return Response('IDK', 200)
                return Response("Messaging task no longer valid", 200)
            return Response("Unknown contact_id", 200)
        else:
            return Response("Failure. Email config does not exist", 200) # Should not repeat        


if __name__ == '__main__':
    data = {
        "email_target_details": {
            "janium_campaign_id": "5598484a-2923-403f-bfdd-5a1e354792c7",
            "email_config_id":  "ab59f3e9-0719-4858-9bff-a5548ceaca86", # nic@janium.io
            "contact_id": "00001317-1c52-40ba-a8eb-04be0998a180",
            "contact_first_name": "Nicolas",
            "contact_full_name": "Nicolas Arnold",
            "contact_email": "narnold113@gmail.com",
            "email_subject": "Janium Says Hello",
            "email_body": r'<html> <body> <div> Hello, {FirstName}</div></body></html>'
            # "preview_text": "This is lovely preview text"
        }
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
