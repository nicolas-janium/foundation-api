from uuid import uuid4

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity

from foundation_api import check_json_header
from foundation_api.V1.sa_db.model import db
from foundation_api.V1.sa_db.model import User, Ulinc_config, Credentials, Cookie, Email_config
from foundation_api.V1.utils.ulinc import get_ulinc_client_info
from foundation_api.V1.utils.ses import send_single_sender_verification_email, verify_ses_dkim, is_single_sender_verified

mod_onboard = Blueprint('onboard', __name__, url_prefix='/api/v1')

@mod_onboard.route('/ulinc_config', methods=['POST'])
@jwt_required()
@check_json_header
def create_ulinc_config(): 
    """
    Required JSON keys: ulinc_username, ulinc_password, ulinc_li_email
    """
    user_id = get_jwt_identity()
    if json_body := request.get_json():
        if user := db.session.query(User).filter(User.user_id == user_id).first():
            if janium_account := user.account:
                if db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_li_email == json_body['ulinc_li_email']).first():
                    return jsonify({"message": "Ulinc config with that LI email already exists"})
                ulinc_credentials_id = str(uuid4())
                ulinc_credentials = Credentials(
                    ulinc_credentials_id,
                    json_body['ulinc_username'],
                    json_body['ulinc_password']
                )
                db.session.add(ulinc_credentials)

                ulinc_client_info = get_ulinc_client_info(json_body['ulinc_username'], json_body['ulinc_password'], json_body['ulinc_li_email'])

                if ulinc_client_info == "There is no Ulinc LinkedIn Email for this Ulinc Account":
                    return jsonify({"message": "Incorrect Ulinc LI email"})

                if not ulinc_client_info['is_login']:
                    return jsonify({"message": "Invalid Ulinc credentials"})

                if not ulinc_client_info['is_business']:
                    return jsonify({"message": "Ulinc account is not business"})

                ulinc_cookie = Cookie(
                    str(uuid4()),
                    1,
                    ulinc_client_info['user_cookie']
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
                    ulinc_client_info['ulinc_is_active']
                )
                db.session.add(new_ulinc_config)
                db.session.commit()
                return jsonify({"message": "Ulinc config successfully created"})
            return jsonify({"message": "Janium account not found"})
        return jsonify({"message": "User not found"})
    return jsonify({"message": "JSON body is missing"})
            

# def send_forwarding_verification_email(recipient='nic@janium.io'):
#     with app.app_context():
#         mail.send_email(
#             from_email='noreply@janium.io',
#             to_email=recipient,
#             subject="Janium Forwarding Verification",
#             text="Test. Please ignore or delete"
#         )

@mod_onboard.route('/email_config', methods=['POST'])
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
                new_email_config = Email_config(
                    str(uuid4()),
                    janium_account.account_id,
                    json_body['from_full_name'],
                    json_body['from_address']
                )
                db.session.add(new_email_config)

                send_single_sender_verification_email(new_email_config.from_address)
                new_email_config.is_ses_single_sender_requested = True

                db.session.commit()
                return jsonify({"message": "Email config created successfully"})
            return jsonify({"message": "Janium account not found"})
        return jsonify({"message": "User not found"})
    return jsonify({"message": "JSON body is missing"})

# @mod_onboard.route('/send_forwarding_verification_email', methods=['GET'])
# @jwt_required()
# def send_forwarding_verification_email_route():
#     """
#     Required query params: email_config_id
#     """
#     email_config_id = request.args.get('email_config_id')
#     if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
#         send_forwarding_verification_email(email_config.from_address)
#         return jsonify({'message': 'Email sent'})
#     return jsonify({"message": "Email config not found"})

@mod_onboard.route('/email_config', methods=['GET'])
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
                    "is_ses_dkim_requested": email_config.is_ses_dkim_requested,
                    "is_ses_dkim_verified": email_config.is_ses_dkim_verified,
                    "is_email_forward_verified": email_config.is_email_forward_verified
                }
            )
        return jsonify({"message": "Email config not found"})
    return jsonify({"message": "Missing email_config_id parameter"})

@mod_onboard.route('/email_configs', methods=['GET'])
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
                        "is_ses_dkim_requested": email_config.is_ses_dkim_requested,
                        "is_ses_dkim_verified": email_config.is_ses_dkim_verified,
                        "is_email_forward_verified": email_config.is_email_forward_verified
                    }
                )
            return jsonify(email_configs)
        return jsonify({"message": "Janium account not found"})
    return jsonify({"message": "User not found"})

@mod_onboard.route('/verify_forwarding', methods=['GET'])
@jwt_required()
def verify_forwarding():
    """
    Required query params: email_config_id
    """
    if email_config_id := request.args.get('email_config_id'):
        if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
            if email_config.is_email_forward_verified:
                return jsonify({"message": "Email forwarding is verified"})
            return jsonify({"message": "Email forwarding is not verified"})
        return jsonify({"message": "Email config not found"})
    return jsonify({"message": "Missing email_config_id parameter"})

@mod_onboard.route('/verify_dkim', methods=['GET'])
@jwt_required()
def verify_dkim():
    """
    Required query params: email_config_id
    """
    if email_config_id := request.args.get('email_config_id'):
        if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == email_config_id).first():
            from_address = email_config.from_address
            verify_dkim_response = verify_ses_dkim(from_address)
            if verify_dkim_response['status'] == 'success':
                email_config.is_ses_dkim_verified = 1
                db.session.commit()
                return jsonify({'message': 'Dkim verified'})
            elif verify_dkim_response['status'] == 'pending':
                email_config.is_ses_dkim_requested = 1
                db.session.commit()
                return jsonify(
                    {
                        'message': 'Dkim verification pending',
                        'data': [
                            {
                                'name': '{}._domainkey.{}'.format(token, from_address[from_address.index('@') + 1 : ]),
                                'type': 'CNAME',
                                'value': '{}.dkim.amazonses.com'.format(token)
                            }
                            for token in verify_dkim_response['dkim_tokens']
                        ]
                    }
                )
            elif verify_dkim_response['status'] == 'started':
                email_config.is_ses_dkim_requested = 1
                db.session.commit()
                return jsonify(
                    {
                        'message': 'Dkim verification started',
                        'data': [
                            {
                                'name': '{}._domainkey.{}'.format(token, from_address[from_address.index('@') + 1 : ]),
                                'type': 'CNAME',
                                'value': '{}.dkim.amazonses.com'.format(token)
                            }
                            for token in verify_dkim_response['dkim_tokens']
                        ]
                    }
                )
        return jsonify({"message": "Email config not found"})
    return jsonify({"message": "Missing email_config_id parameter"})
