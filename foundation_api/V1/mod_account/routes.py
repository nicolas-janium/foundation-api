import os
import random
import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from threading import Thread

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_account.models import User, Account, Ulinc_config, Credentials, Cookie
from foundation_api.V1.utils.get_ulinc import get_ulinc_client_info

mod_account = Blueprint('account', __name__, url_prefix='/api/v1')

@mod_account.route('/ulinc_config', methods=['POST'])
@jwt_required()
def create_ulinc_config():
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if janium_accounts := user.accounts:
        janium_account = janium_accounts[0] # Users are only associated with one Janium Campaign

        if db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_li_email == json_body['ulinc_li_email']).first():
            return jsonify({"message": "Ulinc config with that LI email already exists"})

        ulinc_credentials_id = str(uuid4())
        ulinc_credentials = Credentials(
            ulinc_credentials_id,
            json_body['ulinc_username'],
            json_body['ulinc_password'],
            User.system_user_id
        )
        db.session.add(ulinc_credentials)

        ulinc_client_info = get_ulinc_client_info(json_body['ulinc_username'], json_body['ulinc_password'], json_body['ulinc_li_email'])

        if ulinc_client_info == "There is no Ulinc LinkedIn Email for this Ulinc Account":
            return jsonify({"message": "Incorrect Ulinc LI email"})

        if not ulinc_client_info['is_login']:
            return jsonify({"message": "Invalid Ulinc credentials"})
        
        if not ulinc_client_info['is_business']:
            return jsonify({"message": "Ulinc account in not business"})

        ulinc_cookie = Cookie(
            str(uuid4()),
            1,
            ulinc_client_info['user_cookie'],
            User.system_user_id
        )
        db.session.add(ulinc_cookie)
        new_ulinc_config_id = str(uuid4())
        new_ulinc_config = Ulinc_config(
            new_ulinc_config_id,
            janium_account.account_id,
            ulinc_credentials_id,
            ulinc_cookie.cookie_id,
            ulinc_client_info['ulinc_client_id'],
            ulinc_client_info['webhooks']['new_connection'],
            ulinc_client_info['webhooks']['new_message'],
            ulinc_client_info['webhooks']['send_message'],
            json_body['ulinc_li_email'],
            ulinc_client_info['ulinc_is_active'],
            User.system_user_id
        )
        db.session.add(new_ulinc_config)
        db.session.commit()
        return jsonify({"message": "Ulinc config successfully created"})

@mod_account.route('/get_ulinc_configs', methods=['GET'])
@jwt_required()
def get_ulinc_configs():
    # json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if janium_accounts := user.accounts:
        janium_account_id = janium_accounts[0].account_id # Users are only associated with one Janium Campaign
        janium_account = db.session.query(Account).filter(Account.account_id == janium_account_id).first()

        ulinc_configs = []

        for ulinc_config in janium_account.ulinc_configs:
            ulinc_configs.append(
                {
                    "ulinc_config_id": ulinc_config.ulinc_config_id,
                    "ulinc_li_email": ulinc_config.ulinc_li_email,
                    "ulinc_is_active": ulinc_config.ulinc_is_active
                }
            )
        
        return jsonify(ulinc_configs)
        
