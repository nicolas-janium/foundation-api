from datetime import datetime
from uuid import uuid4

from flask import Blueprint, jsonify, request, current_app, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity

from foundation_api import check_json_header
from foundation_api import check_json_header

from foundation_api.V1.sa_db.model import Time_zone, db
from foundation_api.V1.sa_db.model import User, Account, Ulinc_config, Credentials, Cookie, Contact, Action, Janium_campaign, Ulinc_campaign, Time_zone
from foundation_api.V1.utils.ulinc import get_ulinc_tasks_count

mod_home = Blueprint('home', __name__, url_prefix='/api/v1')

@mod_home.route('/account', methods=['GET'])
@jwt_required()
def get_account():
    """
    Required query params: None
    """
    user_id = get_jwt_identity()
    if user := db.session.query(User).filter(User.user_id == user_id).first():
        janium_account = user.account
        return jsonify(
            {
                # "janium_account_id": janium_account.account_id,
                "is_sending_emails": janium_account.is_sending_emails,
                "is_sending_li_messages": janium_account.is_sending_li_messages,
                "is_receiving_dte": janium_account.is_receiving_dte,
                "time_zone_code": janium_account.time_zone.time_zone_code,
                "is_active": janium_account.is_active(),
                "is_payment_active": janium_account.is_payment_active()
            }
        )
    return make_response(jsonify({"message": "User not found"}), 401)

@mod_home.route('/account', methods=['PUT'])
@jwt_required()
@check_json_header
def update_account():
    """
    Required JSON keys: is_sending_emails, is_sending_li_messages, is_receiving_dte, is_active, time_zone_code
    """
    user_id = get_jwt_identity()
    if user := db.session.query(User).filter(User.user_id == user_id).first():
        if json_body := request.get_json():
            if time_zone := db.session.query(Time_zone).filter(Time_zone.time_zone_code == json_body['time_zone_code']).first():
                janium_account = user.account

                # Update Account fields
                janium_account.is_sending_emails = json_body['is_sending_emails']
                janium_account.is_sending_li_messages = json_body['is_sending_li_messages']
                janium_account.is_receiving_dte = json_body['is_receiving_dte']
                janium_account.is_active = json_body['is_active']
                janium_account.time_zone_id = time_zone.time_zone_id
                return jsonify({"message": "success"})
            return make_response(jsonify({"message": "Unknown time_zone_code"}), 400)
        return jsonify({"message": "JSON body is missing"})
    return make_response(jsonify({"message": "User not found"}), 401)


@mod_home.route('/ulinc_configs', methods=['GET'])
@jwt_required()
def get_ulinc_configs():
    """
    Required query params: None
    """
    user_id = get_jwt_identity()
    if user := db.session.query(User).filter(User.user_id == user_id).first():
        janium_account = user.account
        ulinc_configs = []

        for ulinc_config in janium_account.ulinc_configs:
            ulinc_configs.append(
                {
                    "ulinc_config_id": ulinc_config.ulinc_config_id,
                    "ulinc_li_email": ulinc_config.ulinc_li_email,
                    "ulinc_is_active": ulinc_config.ulinc_is_active,
                    "ulinc_is_working": ulinc_config.is_working,
                    "ulinc_tasks_in_queue": get_ulinc_tasks_count(ulinc_config.ulinc_client_id, ulinc_config.cookie),
                    "summary_data": ulinc_config.get_summary_data(),
                    "janium_account_is_active": janium_account.is_active(),
                    "janium_account_is_payment_active": janium_account.is_payment_active()
                }
            )

        return jsonify(ulinc_configs)
    return make_response(jsonify({"message": "User not found"}), 401)

@mod_home.route('/ulinc_config', methods=['GET'])
@jwt_required()
def get_ulinc_config():
    """
    Required query params: ulinc_config_id
    """
    user_id = get_jwt_identity()
    if ulinc_config_id := request.args.get('ulinc_config_id'):
        if ulinc_config := db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == ulinc_config_id).first():
            janium_campaigns = []
            for janium_campaign in ulinc_config.janium_campaigns:
                janium_campaigns.append(
                    {
                        "janium_campaign_id": janium_campaign.janium_campaign_id,
                        "janium_campaign_name": janium_campaign.janium_campaign_name,
                        "janium_campaign_type": "Messenger" if janium_campaign.is_messenger else "Connector",
                        "janium_campaign_contacts": janium_campaign.get_total_num_contacts(),
                        "janium_campaign_connected": janium_campaign.get_total_num_connections(),
                        "janium_campaign_replied": janium_campaign.get_total_num_responses()
                    }
                )
            return jsonify(
                {
                    "ulinc_config_id": ulinc_config.ulinc_config_id,
                    "ulinc_is_working": ulinc_config.is_working,
                    "janium_campaigns": janium_campaigns,
                    "new_connections": ulinc_config.get_dte_new_connections(),
                    "new_messages": ulinc_config.get_dte_new_messages(),
                    "vm_tasks": ulinc_config.get_dte_vm_tasks()
                }
            )
        return make_response(jsonify({"message": "Unknown ulinc_config_id value"}), 400)
    return make_response(jsonify({"message": "Missing ulinc_config_id param"}), 400)

# @mod_home.route('/dte_click', methods=['POST'])
# @jwt_required()
# def dte_click():
#     """
#     Required JSON keys: click_type (new_connection, dq, continue), contact_id
#     """
#     json_body = request.get_json(force=True)

#     if json_body['click_type'] == 'new_connection':
#         new_action = Action(str(uuid4()), json_body['contact_id'], 8, datetime.utcnow(), None)
#     elif json_body['click_type'] == 'dq':
#         new_action = Action(str(uuid4()), json_body['contact_id'], 11, datetime.utcnow(), None)
#     elif json_body['click_type'] == 'continue':
#         new_action = Action(str(uuid4()), json_body['contact_id'], 14, datetime.utcnow(), None)
    
#     db.session.add(new_action)
#     db.session.commit()
#     return jsonify({"message": "Action recorded successfully"})
