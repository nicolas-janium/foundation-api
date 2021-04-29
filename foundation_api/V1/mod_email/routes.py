import email
import json
import os
import random
import string
from datetime import datetime, timedelta, timezone
from threading import Thread
from uuid import uuid4

from flask import Blueprint, jsonify, make_response, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_email.models import Action
from sqlalchemy import and_, or_

mod_email = Blueprint('email', __name__, url_prefix='/api/v1')

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

    # O365 get original email message id
    references = str(email_message.get('References')).split(',')
    for reference in references:
        print(reference)
        if original_send_action := db.session.query(Action).filter(and_(Action.email_message_id == reference, Action.action_type_id == 4)).first():
            if original_receive_action := db.session.query(Action).filter(and_(Action.email_message_id == reference, Action.action_type_id == 6)).first():
                pass
            else:
                new_action = Action(str(uuid4()), original_send_action.contact_id, 6, datetime.utcnow(), None, None, reference)
                db.session.add(new_action)
                db.session.commit()

    return jsonify({"message": 'text'})
