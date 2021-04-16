import os
import random
import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from threading import Thread

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_campaign.models import User, Account, Ulinc_config, Credentials, Cookie, Contact, Action, Janium_campaign

mod_campaign = Blueprint('campaign', __name__, url_prefix='/api/v1')

@mod_campaign.route('/create_janium_campaign', methods=['POST'])
@jwt_required()
def create_janium_campaign():
    """
    Required JSON keys: ulinc_config_id, email_config_id, janium_campaign_name, janium_campaign_description, queue_start_time, queue_end_time
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if janium_accounts := user.accounts:
        janium_account = janium_accounts[0].account # Users are only associated with one Janium Campaign

        if db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_name == json_body['janium_campaign_name']).first():
            return jsonify({"message": "A Janium campaign with that name already exists"})

        new_janium_campaign = Janium_campaign(
            str(uuid4()),
            janium_account.account_id,
            json_body['ulinc_config_id'],
            json_body['email_config_id'],
            json_body['janium_campaign_name'],
            json_body['janium_campaign_description'],
            False, # Not doing messenger campaigns for the MVP
            False,
            json_body['queue_start_time'],
            json_body['queue_end_time'],
            user_id
        )
        db.session.add(new_janium_campaign)
        db.session.commit()
        return jsonify({"message": "Janium campaign created successfully"})
