from datetime import datetime, timedelta
import os
from uuid import uuid4

from flask import Blueprint, json, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from foundation_api import check_json_header
from foundation_api.V1.utils.ulinc import get_ulinc_client_info
from foundation_api.V1.sa_db.model import db
from foundation_api.V1.sa_db.model import Janium_campaign, Ulinc_campaign, Janium_campaign_step, Ulinc_config, Account, User, Credentials, Cookie
from foundation_api.V1.utils import google_tasks


mod_ulinc = Blueprint('ulinc', __name__, url_prefix='/api/v1')


@mod_ulinc.route('/ulinc_config', methods=['POST'])
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

@mod_ulinc.route('/trigger_ulinc_csv_polling', methods=['GET'])
@jwt_required()
def trigger_ulinc_csv_polling():
    """
    Required query params: ulinc_config_id
    """
    gct_client = google_tasks.create_tasks_client()
    user_id = get_jwt_identity()
    if ulinc_config_id := request.args.get('ulinc_config_id'):
        if ulinc_config := db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == ulinc_config_id).first():
            for ulinc_campaign in ulinc_config.ulinc_campaigns:
                payload = {
                    'ulinc_config_id': ulinc_config.ulinc_config_id,
                    'ulinc_campaign_id': ulinc_campaign.ulinc_campaign_id
                }
                if os.getenv('FLASK_ENV') == 'production':
                    gct_csv_parent = google_tasks.create_tasks_parent(gct_client, os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), 'poll-ulinc-csv')
                    task = google_tasks.create_app_engine_task('/api/v1/tasks/poll_ulinc_csv', payload)
                else:
                    gct_csv_parent = google_tasks.create_tasks_parent(gct_client, 'foundation-staging-305217', 'us-central1', queue='poll-ulinc-csv')
                    task = google_tasks.create_url_task(os.getenv("BACKEND_API_URL"), '/api/v1/tasks/poll_ulinc_csv', payload)
                task_response = google_tasks.send_task(gct_client, gct_csv_parent, task)
            return jsonify({"message": "success"})
        return make_response(jsonify({"message": "Unknown ulinc_config_id value"}), 400)
    return make_response(jsonify({"message": "Missing ulinc_config_id param"}), 400)

@mod_ulinc.route('/trigger_ulinc_webhook_polling', methods=['GET'])
@jwt_required()
def trigger_ulinc_webhook_polling():
    """
    Required query params: ulinc_config_id
    """
    gct_client = google_tasks.create_tasks_client()
    user_id = get_jwt_identity()
    if ulinc_config_id := request.args.get('ulinc_config_id'):
        if ulinc_config := db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == ulinc_config_id).first():
            for webhook in ulinc_config.get_webhooks():
                payload = {
                    'ulinc_config_id': ulinc_config.ulinc_config_id,
                    'webhook_url': webhook['url'],
                    'webhook_type': webhook['type']
                }
                if os.getenv('FLASK_ENV') == 'production':
                    gct_csv_parent = google_tasks.create_tasks_parent(gct_client, os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), 'poll-ulinc-webhook')
                    task = google_tasks.create_app_engine_task('/api/v1/tasks/poll_ulinc_webhook', payload)
                else:
                    gct_csv_parent = google_tasks.create_tasks_parent(gct_client, 'foundation-staging-305217', 'us-central1', queue='poll-ulinc-webhook')
                    task = google_tasks.create_url_task(os.getenv("BACKEND_API_URL"), '/api/v1/tasks/poll_ulinc_webhook', payload)
                task_response = google_tasks.send_task(gct_client, gct_csv_parent, task)
            return jsonify({"message": "success"})
        return make_response(jsonify({"message": "Unknown ulinc_config_id value"}), 400)
    return make_response(jsonify({"message": "Missing ulinc_config_id param"}), 400)
