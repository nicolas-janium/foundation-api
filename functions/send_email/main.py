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
import minify_html

from model import (Action, Contact, Email_config, Janium_campaign_step, create_gcf_db_engine,
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

def send_email_with_ses(email_config, janium_campaign_step, contact, session):
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
            if janium_campaign_step := session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == json_body['janium_campaign_step_id']).first():
                if contact := session.query(Contact).filter(Contact.contact_id == json_body['contact_id']).first():
                    if contact.is_messaging_task_valid():
                        if send_email_with_ses(email_config, janium_campaign_step, contact, session):
                            return Response('Success', 200)
                        return Response('IDK', 200)
                    return Response("Messaging task no longer valid", 200)
                return Response("Unknown contact_id", 200)
        return Response("Failure. Email config does not exist", 200) # Should not repeat        


if __name__ == '__main__':
    data = {
        "janium_campaign_id": "5598484a-2923-403f-bfdd-5a1e354792c7",
        "email_config_id":  "ab59f3e9-0719-4858-9bff-a5548ceaca86", # nic@janium.io
        "janium_campaign_step_id": "7fc67976-953b-4c1d-8902-3035932b7287",
        "ulinc_campaign_id": "753d27be-c5e5-4b12-806d-b9bf60ccab5f",
        "contact_id": "0093d012-c5a7-48ca-92e8-2aca71c9f0ed"
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)

    # key_words_dict = {
    #     "FirstName": "Tim",
    #     "Location": "SF",
    #     "Company": "Google"
    # }
    # email_html = r"<html>Hello, {FirstName}, how is it in {Location} at {Company}?</html>"

    # email_html = insert_key_words(email_html=email_html, key_words_dict=key_words_dict)
    # print(email_html)
