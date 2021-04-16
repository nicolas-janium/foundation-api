from datetime import datetime, timedelta, timezone
from uuid import uuid4

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_onboard.models import User, Account, Ulinc_config, Credentials, Cookie, Email_config, Email_server
from foundation_api.V1.utils.ulinc import get_ulinc_client_info

mod_onboard = Blueprint('onboard', __name__, url_prefix='/api/v1')

@mod_onboard.route('/ulinc_config', methods=['POST'])
@jwt_required()
def create_ulinc_config():
    """
    Required JSON keys: ulinc_username, ulinc_password, ulinc_li_email
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if janium_accounts := user.accounts:
        janium_account = janium_accounts[0].account # Users are only associated with one Janium Campaign

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

@mod_onboard.route('/email_config', methods=['POST'])
@jwt_required()
def create_email_config():
    """
    Required JSON keys: email_app_username, email_app_password, email_server_name, from_full_name, reply_to_address and is_sendgrid.

    If is_sendgrid is true, required JSON keys: from_email_address, company_address_line_1, company_address_line_1, city, state, zip_code and country.

    I suggest that every user sends emails through sendgrid and we read email inboxes with app passcodes
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if credentials_list := db.session.query(Credentials).filter(Credentials.username == json_body['email_app_username']).all():
        for credentials in credentials_list:
            if credentials.email_config:
                return jsonify({"message": "Email config with {} email app username already exists".format(json_body['email_app_username'])})

    # if db.session.query(Email_config).filter(Email_config.credentials.username == json_body['email_app_username']).first(): # This don't workkkkkk
    #     return jsonify({"message": "Email config with {} email app username already exists".format(json_body['email_app_username'])})

    if janium_accounts := user.accounts:
        janium_account = janium_accounts[0].account # Users are only associated with one Janium Campaign

        email_server = db.session.query(Email_server).filter(Email_server.email_server_name == json_body['email_server_name']).first()

        new_credentials = Credentials(
            str(uuid4()),
            json_body['email_app_username'],
            json_body['email_app_password'],
            user.user_id
        )
        db.session.add(new_credentials)

        new_email_config = Email_config(
            str(uuid4()),
            janium_account.account_id,
            new_credentials.credentials_id,
            email_server.email_server_id,
            json_body['is_sendgrid'],
            None,
            False,
            user.user_id,
            json_body['from_full_name'],
            json_body['reply_to_address']
        )
        db.session.add(new_email_config)
        db.session.commit()

        return jsonify({"message": "Email config created successfully"})

@mod_onboard.route('/email_config', methods=['GET'])
@jwt_required()
def get_email_config():
    """
    Required JSON keys: email_config_id
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()

    email_config = db.session.query(Email_config).filter(Email_config.email_config_id == json_body['email_config_id']).first()

    return jsonify(
        {
            "email_config_id": email_config.email_config_id,
            "email_app_username": email_config.credentials.username,
            "email_server_name": email_config.email_server.email_server_name,
            "from_full_name": email_config.from_full_name,
            "reply_to_address": email_config.reply_to_address,
            "is_sendgrid": email_config.is_sendgrid
        }
    )

@mod_onboard.route('/email_configs', methods=['GET'])
@jwt_required()
def get_email_configs():
    """
    Required JSON keys: None
    """
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if janium_accounts := user.accounts:
        janium_account = janium_accounts[0].account

        email_configs = []
        for email_config in janium_account.email_configs:
            email_configs.append(
                {
                    "email_config_id": email_config.email_config_id,
                    "email_app_username": email_config.credentials.username,
                    "email_server_name": email_config.email_server.email_server_name,
                    "from_full_name": email_config.from_full_name,
                    "reply_to_address": email_config.reply_to_address,
                    "is_sendgrid": email_config.is_sendgrid
                }
            )

        return jsonify(email_configs)
