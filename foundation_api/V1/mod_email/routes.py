import email
from email.message import EmailMessage
import json
import os
import urllib.parse as urlparse
from datetime import datetime
from urllib.parse import parse_qs
from uuid import uuid4

import requests
from bs4 import BeautifulSoup as Soup
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from foundation_api import check_json_header
from foundation_api.V1.sa_db.model import (Action, Contact, Dte, Dte_sender,
                                           Email_config, User, db)
from foundation_api.V1.utils.ses import (create_ses_identiy_dkim_tokens,
                                         is_ses_identity_dkim_verified,
                                         is_ses_identity_verified,
                                         send_forwarding_rule_test_email,
                                         send_ses_identity_verification_email)
from nameparser import HumanName
from sqlalchemy import and_, or_, text
from sqlalchemy.orm.attributes import flag_modified


mod_email = Blueprint('email', __name__, url_prefix='/api/v1')


@mod_email.route('/email_config', methods=['POST'])
@jwt_required()
@check_json_header
def create_email_config():
    """
    Required JSON keys: from_address, from_full_name
    """
    user_id = get_jwt_identity()
    if json_body := request.get_json():
        if user := db.session.query(User).filter(User.user_id == user_id).first():
            if janium_account := user.account:
                if existing_email_config := db.session.query(Email_config).filter(Email_config.from_address == json_body['from_address']).first():
                    return jsonify({"message": "Email config already exists"})
                from_full_name = json_body['from_full_name']
                from_address = json_body['from_address']
                name = HumanName(full_name=from_full_name)
                email_server = "8ce10791-240e-4cdc-a95c-c7e0876dc19a"
                if json_body['is_gmail']:
                    email_server = "936dce84-b50f-4b72-824f-b01989b20500"
                new_email_config = Email_config(
                    str(uuid4()),
                    janium_account.account_id,
                    json_body['from_full_name'],
                    json_body['from_address'],
                    "{}.{}.{}@inbound.janium.io".format(str(name.first).lower(), str(name.last).lower(), str(str(from_address).split('@')[1]).split('.')[0]),
                    email_server_id=email_server
                )
                db.session.add(new_email_config)
                db.session.commit()

                send_ses_identity_verification_email(new_email_config.from_address)
                new_email_config.is_ses_identity_requested = True
                db.session.commit()
                return jsonify({"message": "Email config created successfully"})
            return jsonify({"message": "Janium account not found"})
        return jsonify({"message": "User not found"})
    return jsonify({"message": "JSON body is missing"})

@mod_email.route('/email_config', methods=['PUT'])
@jwt_required()
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

    return jsonify({"message": "Unknown email_config_id"})

@mod_email.route('/email_config', methods=['GET'])
@jwt_required()
def get_email_config():
    """
    Required query params: email_config_id
    """
    if email_config_id := request.args.get('email_config_id'):
        if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
            return jsonify(
                {
                    "email_config_id": email_config.email_config_id,
                    "from_address": email_config.from_address,
                    "from_full_name": email_config.from_full_name,
                    "is_ses_identity_requested": email_config.is_ses_identity_requested,
                    "is_ses_identity_verified": email_config.is_ses_identity_verified,
                    "is_ses_dkim_requested": email_config.is_ses_dkim_requested,
                    "is_ses_dkim_verified": email_config.is_ses_dkim_verified,
                    "is_email_forwarding_rule_verified": email_config.is_email_forwarding_rule_verified,
                    "inbound_parse_email": email_config.inbound_parse_email,
                    "is_gmail": True if email_config.email_server_id == '936dce84-b50f-4b72-824f-b01989b20500' else False,
                    "gmail_forwarding_confirmation_code": email_config.gmail_forwarding_confirmation_code
                }
            )
        return jsonify({"message": "Unknown email_config_id"})
    return jsonify({"message": "Missing email_config_id parameter"})

@mod_email.route('/email_configs', methods=['GET'])
@jwt_required()
def get_email_configs():
    """
    Required query params: None
    """
    user_id = get_jwt_identity()
    if user := db.session.query(User).filter(User.user_id == user_id).first():
        if janium_account := user.account:
            email_configs = []
            for email_config in janium_account.email_configs:
                email_configs.append(
                    {
                        "email_config_id": email_config.email_config_id,
                        "from_address": email_config.from_address,
                        "from_full_name": email_config.from_full_name,
                        "is_ses_identity_requested": email_config.is_ses_identity_requested,
                        "is_ses_identity_verified": email_config.is_ses_identity_verified,
                        "is_ses_dkim_requested": email_config.is_ses_dkim_requested,
                        "is_ses_dkim_verified": email_config.is_ses_dkim_verified,
                        "is_email_forwarding_rule_verified": email_config.is_email_forwarding_rule_verified,
                        "inbound_parse_email": email_config.inbound_parse_email,
                        "is_gmail": True if email_config.email_server_id == '936dce84-b50f-4b72-824f-b01989b20500' else False
                    }
                )
            return jsonify(email_configs)
        return jsonify({"message": "Janium account not found"})
    return jsonify({"message": "User not found"})

@mod_email.route('/is_ses_identity_verified', methods=['GET'])
@jwt_required()
def is_ses_identity_verified_route():
    """
    Required query params: email_config_id
    """
    email_config_id = request.args.get('email_config_id')
    if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
        if is_ses_identity_verified(email_config.from_address):
            email_config.is_ses_identity_verified = True
            db.session.commit()
            return jsonify({"message": True})
        return jsonify({"message": False})
    return jsonify({"message": "Unknown email_config_id"})

@mod_email.route('/send_forwarding_rule_test_email', methods=['GET'])
@jwt_required()
def send_forwarding_rule_test_email_route():
    """
    Required query params: email_config_id
    """
    email_config_id = request.args.get('email_config_id')
    if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
        send_forwarding_rule_test_email(email_config.from_address)
        return jsonify({"message": "Forwarding test email sent"})
    return jsonify({"message": "Unknown email_config_id"})

@mod_email.route('/create_ses_identity_dkim_tokens', methods=['GET'])
@jwt_required()
def create_ses_identity_dkim_tokens_route():
    """
    Required query params: email_config_id
    """
    email_config_id = request.args.get('email_config_id')
    if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
        tokens = create_ses_identiy_dkim_tokens(email_config.from_address)
        return jsonify(tokens)
    return jsonify({"message": "Unknown email_config_id"})

# @mod_email.route('/enable_ses_identity_dkim_signing', methods=['GET'])
# @jwt_required()
# def enable_ses_identity_dkim_signing_route():
#     """
#     Required query params: email_config_id
#     """
#     email_config_id = request.args.get('email_config_id')
#     if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
#         enable_ses_identity_dkim_signing(email_config.from_address)
#         return jsonify({"message": "DKIM signing enabled"})
#     return jsonify({"message": "Unknown email_config_id"})

@mod_email.route('/is_ses_identity_dkim_verified', methods=['GET'])
@jwt_required()
def is_ses_identity_dkim_verified_route():
    """
    Required query params: email_config_id
    """
    email_config_id = request.args.get('email_config_id')
    if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
        if is_ses_identity_dkim_verified(email_config.from_address):
            return jsonify({"message": True})
        return jsonify({"message": False})
    return jsonify({"message": "Unknown email_config_id"})

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

    is_from_outlook = True if 'outlook' in email_message.get('Message-ID') else False
    to_address = str(email_message.get('To'))
    index = to_address.index('<')
    to_address = to_address[index + 1: len(to_address) - 1]

    forwarded_to_address = str(email_message.get('X-Forwarded-To'))

    ### For gmail, inbound_parse_email is in X-Forwarded-To field. For O365, it's in the To field ###
    if 'Janium Forwarding Rule Test Email' in json.dumps(req_dict):
        if email_config := db.session.query(Email_config).filter(Email_config.inbound_parse_email.in_([to_address, forwarded_to_address])).first():
            email_config.is_email_forwarding_rule_verified = True
            flag_modified(email_config, 'is_email_forwarding_rule_verified')
            db.session.commit()
    elif 'forwarding-noreply@google.com' in json.dumps(req_dict) or 'Gmail Forwarding Confirmation' in json.dumps(req_dict):
        if email_config := db.session.query(Email_config).filter(Email_config.inbound_parse_email.in_([to_address, forwarded_to_address])).first():
            body = str(body)
            confirmation_code_index = body.index('Confirmation code')
            confirmation_code = body[confirmation_code_index + 19: confirmation_code_index + 28]
            email_config.gmail_forwarding_confirmation_code = confirmation_code
            flag_modified(email_config, 'gmail_forwarding_confirmation_code')
            db.session.commit()
    else:
        references = str(email_message.get('References')).split(',')
        for reference in references:
            reference = str(reference).replace('<', '').replace('>', '').split('@')[0]
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




# def verify_sendgrid_single_sender(email_message):
#     body = None
#     html_body = None
#     for part in email_message.walk():
#         ctype = part.get_content_type()
#         cdispo = str(part.get('Content-Disposition'))

#         if ctype == 'text/plain' and 'attachment' not in cdispo:
#             body = part.get_payload(decode=True)  # decode
#         elif ctype == 'text/html' and 'attachment' not in cdispo:
#             html_body = part.get_payload(decode=True)  # decode
#     if html_body:
#         soup = Soup(html_body, 'html.parser')
#         links = soup.find_all('a')
#         for link in links:
#             # print(link)
#             # print('\n')
#             if link.text == 'Verify Single Sender':
#                 verify_link = link['href']

#         # verify_link = links[4]['href']
#         # print(verify_link)

#         req_session = requests.Session()
#         response = req_session.get(verify_link)
#         for item in response.history:
#             if 'token' in item.headers.get('Location'):
#                 location = item.headers.get('Location')
#                 parsed = urlparse.urlparse(location)
#                 token = parse_qs(parsed.query)['token'][0]
#                 print(token)

#                 sendgrid_headers = {
#                     'authorization': "Bearer {}".format(os.getenv('SENDGRID_API_KEY'))
#                 }
#                 url = "https://api.sendgrid.com/v3/verified_senders/verify/{}".format(token)
#                 response = requests.get(url=url, headers=sendgrid_headers)
#                 if response.ok:
#                     return 1
#                 else:
#                     return None
#     return None
