import email
import json
import os
import random
import string
from datetime import datetime, timedelta, timezone
from threading import Thread
from uuid import uuid4
import urllib.parse as urlparse
from urllib.parse import parse_qs

import requests
from bs4 import BeautifulSoup as Soup
from flask import Blueprint, jsonify, make_response, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_email.models import Action
from sqlalchemy import and_, or_

mod_email = Blueprint('email', __name__, url_prefix='/api/v1')

def verify_single_sender(email_message):
    body = None
    html_body = None
    for part in email_message.walk():
        ctype = part.get_content_type()
        cdispo = str(part.get('Content-Disposition'))

        if ctype == 'text/plain' and 'attachment' not in cdispo:
            body = part.get_payload(decode=True)  # decode
        elif ctype == 'text/html' and 'attachment' not in cdispo:
            html_body = part.get_payload(decode=True)  # decode
    if html_body:
        soup = Soup(html_body, 'html.parser')
        links = soup.find_all('a')
        for link in links:
            # print(link)
            # print('\n')
            if link.text == 'Verify Single Sender':
                verify_link = link['href']

        # verify_link = links[4]['href']
        # print(verify_link)

        req_session = requests.Session()
        response = req_session.get(verify_link)
        for item in response.history:
            if 'token' in item.headers.get('Location'):
                location = item.headers.get('Location')
                parsed = urlparse.urlparse(location)
                token = parse_qs(parsed.query)['token'][0]
                print(token)

                sendgrid_headers = {
                    'authorization': "Bearer {}".format(os.getenv('SENDGRID_API_KEY'))
                }
                url = "https://api.sendgrid.com/v3/verified_senders/verify/{}".format(token)
                response = requests.get(url=url, headers=sendgrid_headers)
                if response.ok:
                    return 1
                else:
                    return None
    return None


@mod_email.route('/parse_email', methods=['POST'])
def parse_email():
    """
    Required JSON keys: None
    """
    # envelope = json.loads(request.form.get('envelope'))

    # to_address = envelope['to'][0]
    # from_address = envelope['from']

    # text = request.form.get('text')
    # html = request.form.get('html')
    # subject = request.form.get('subject')

    req_dict = request.form.to_dict()

    email_message = email.message_from_string(req_dict['email'])

    body = ''
    if email_message.is_multipart():
        for part in email_message.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))

            if ctype == 'text/plain' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True)  # decode
            elif ctype == 'text/html' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True)  # decode
                break # Default to html body
    else:
        body = email_message.get_payload(decode=True)

    # Gmail get original email message id
    # print(email_message.get('In-Reply-To'))
    # print(email_message.get('References'))
    if 'Single Sender' in email_message.get('Subject'):
        print("Single Sender verify request from sendgrid")
        if verify_single_sender(email_message):
            print("Sengrid Sender verified")
        else:
            print("Sendgrid Sender not verified")

    # O365 get original email message id
    references = str(email_message.get('References')).split(',')
    for reference in references:
        # print(reference)
        if original_send_action := db.session.query(Action).filter(and_(Action.email_message_id == reference, Action.action_type_id == 4)).first():
            if original_receive_action := db.session.query(Action).filter(and_(Action.email_message_id == reference, Action.action_type_id == 6)).first():
                pass
            else:
                new_action = Action(str(uuid4()), original_send_action.contact_id, 6, datetime.utcnow(), None, None, reference)
                db.session.add(new_action)
                db.session.commit()

    return jsonify({"message": 'text'})
