import email
import json
import os
from datetime import datetime
from uuid import uuid4
import urllib.parse as urlparse
from urllib.parse import parse_qs

import requests
from bs4 import BeautifulSoup as Soup
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from foundation_api.V1.sa_db.model import db, Dte, Dte_sender
from foundation_api.V1.sa_db.model import Action, Email_config, User, Contact
from foundation_api.V1.utils.ses import is_single_sender_verified
from sqlalchemy import and_, or_

mod_email = Blueprint('email', __name__, url_prefix='/api/v1')

def verify_sendgrid_single_sender(email_message):
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

@mod_email.route('/email_config', methods=['PUT'])
def update_email_config():
    """
    Required JSON keys: email_config_id, from_full_name
    """

    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == json_body['email_config_id']).first():
        email_config.from_full_name = json_body['from_full_name']
        db.session.commit()
        return jsonify({"message": "Email config updated successfully"})

    return jsonify({"message": "Invalid email_config_id"})

@mod_email.route('/is_single_sender_verified', methods=['GET'])
@jwt_required()
def is_single_sender_verified_route():
    """
    Required query params: email_config_id
    """
    email_config_id = request.args.get('email_config_id')
    if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
        if is_single_sender_verified(email_config.from_address):
            return jsonify({"message": True})
        return jsonify({"message": False})
    return jsonify({"message": "Email config not found"})

@mod_email.route('/parse_email', methods=['POST'])
def parse_email():
    """
    Required JSON keys: None
    """
    req_dict = request.form.to_dict()
    # pprint(req_dict)
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

    if os.getenv('JANIUM_EMAIL_ID') in json.dumps(req_dict):
        if 'Janium Forwarding Verification' in json.dumps(req_dict):
            recipient_address = str(email_message.get('To'))
            recipient_address = recipient_address[recipient_address.index('<') + 1: recipient_address.index('>')] if '<' in recipient_address else recipient_address
            if email_config := db.session.query(Email_config).filter(Email_config.from_address == recipient_address).first():
                email_config.is_email_forward_verified = 1
                db.session.commit()
        else:
            references = str(email_message.get('References')).split(',')
            for reference in references:
                if original_send_action := db.session.query(Action).filter(and_(Action.email_message_id == reference, Action.action_type_id == 4)).first():
                    if original_receive_action := db.session.query(Action).filter(and_(Action.email_message_id == reference, Action.action_type_id == 6)).first():
                        pass
                    else:
                        new_action = Action(str(uuid4()), original_send_action.contact_id, 6, datetime.utcnow(), None, None, reference)
                        db.session.add(new_action)
                        db.session.commit()

    return jsonify({"message": "text"})

@mod_email.route('/sns', methods=['POST'])
def catch_sns():
    json_body = request.get_json(force=True)
    # print('\n')
    # print(request.headers)
    # print(json_body)

    notif_message = json.loads(json_body['Message'])
    notif_type = notif_message['notificationType']
    if notif_type == 'Complaint':
        notif_recipient = notif_message['complaint']['complainedRecipients'][0]['emailAddress']
    elif notif_type == 'Bounce':
        notif_recipient = notif_message['bounce']['bouncedRecipients'][0]['emailAddress']
    print(notif_type)
    print(notif_recipient)

    contacts = [
        contact for contact in db.session.query(Contact).all()
        if contact.actions.filter(Action.action_type_id == 4).first()
    ]
    for contact in contacts:
        if notif_recipient in contact.get_emails():
            action = Action(
                str(uuid4()),
                contact.contact_id,
                15 if notif_type == 'Bounce' else 7,
                datetime.utcnow(),
                None,
                None,
                json_body['MessageId']
            )
            db.session.add(action)
            db.session.commit()

    return "Message received"

@mod_email.route('/dtes', methods=['GET'])
@jwt_required()
def get_dtes():
    """
    Required Query Params: None
    """
    user_id = get_jwt_identity()

    dte_list = []
    for dte in db.session.query(Dte).all():
        dte_list.append({
            "dte_id": dte.dte_id,
            "dte_name": dte.dte_name,
            "dte_description": dte.dte_description,
            "dte_subject": dte.dte_subject,
            "dte_body": dte.dte_body
        })
    return jsonify(dte_list)

@mod_email.route('/dte_senders', methods=['GET'])
@jwt_required()
def get_dte_senders():
    """
    Required Query Params: None
    """
    user_id = get_jwt_identity()

    dte_sender_list = []
    for dte in db.session.query(Dte_sender).all():
        dte_sender_list.append({
            "dte_sender_id": dte.dte_sender_id,
            "dte_sender_full_name": dte.dte_sender_full_name,
            "dte_sender_from_email": dte.dte_sender_from_email
        })
    return jsonify(dte_sender_list)