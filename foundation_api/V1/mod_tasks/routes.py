from datetime import datetime
import logging
import json
import os

from flask import Blueprint, jsonify, request, make_response
from sqlalchemy import and_
from pprint import pprint
from google.cloud import tasks_v2

from foundation_api.V1.sa_db.model import Email_config, db
from foundation_api.V1.sa_db.model import Account, Ulinc_config, Contact_source, Ulinc_campaign, Janium_campaign, Contact
from foundation_api.V1.utils.refresh_ulinc_data import refresh_ulinc_campaigns, refresh_ulinc_cookie, refresh_ulinc_account_status
from foundation_api.V1.utils.poll_ulinc_webhook import poll_and_save_webhook
from foundation_api.V1.utils.poll_ulinc_csv import poll_and_save_csv
from foundation_api.V1.utils.process_contact_source_handler import process_contact_source_function
from foundation_api.V1.utils.data_enrichment import data_enrichment_function
from foundation_api.V1.utils.send_email import send_email_function
from foundation_api.V1.utils.send_li_message import send_li_message_function, update_ulinc_contact_status
from foundation_api.V1.utils import google_tasks


logger = logging.getLogger('api_tasks')
formatter = logging.Formatter('%(levelname)s - %(message)s')
logHandler = logging.StreamHandler()
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

gc_tasks_client = tasks_v2.CloudTasksClient()

mod_tasks = Blueprint('tasks', __name__, url_prefix='/api/v1/tasks')

@mod_tasks.route('/poll_ulinc_webhook', methods=['POST'])
def poll_ulinc_webhook_task():
    """
    Required JSON keys: ulinc_config_id, webhook_url, webhook_type
    """
    json_body = request.get_json()
    ulinc_config = db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first()
    if poll_and_save_webhook(ulinc_config, json_body['webhook_url'], json_body['webhook_type']) == "success":
        return jsonify({"message": "success"})
    else:
        return make_response(jsonify({"message": "failure"}), 300)

@mod_tasks.route('/poll_ulinc_csv', methods=['POST'])
def poll_ulinc_csv_task():
    """
    Required JSON keys: ulinc_config_id, ulinc_campaign_id
    """
    json_body = request.get_json()
    ulinc_config = db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first()
    ulinc_campaign = db.session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_campaign_id == json_body['ulinc_campaign_id']).first()
    if poll_and_save_csv(ulinc_config, ulinc_campaign) == "success":
        return jsonify({"message": "success"})
    else:
        return make_response(jsonify({"message": "failure"}), 300)

@mod_tasks.route('/process_contact_source', methods=['POST'])
def process_contact_source_task():
    """
    Required JSON keys: account_id, ulinc_config_id, contact_source_id
    """
    json_body = request.get_json(force=True)
    account = db.session.query(Account).filter(Account.account_id == json_body['account_id']).first()
    ulinc_config = db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first()
    contact_source = db.session.query(Contact_source).filter(Contact_source.contact_source_id == json_body['contact_source_id']).first()
    
    if process_contact_source_function(ulinc_config, contact_source):
        return jsonify({"message": "success"})
    return make_response(jsonify({"message": "failure"}), 200) # Should not repeat

@mod_tasks.route('/refresh_ulinc_data', methods=['POST'])
def refresh_ulinc_data_task():
    """
    Required JSON keys: ulinc_config_id
    """
    json_body = request.get_json(force=True)
    ulinc_config = db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first()

    refresh_ulinc_cookie(ulinc_config)
    if ulinc_config.is_working:
        refresh_ulinc_account_status(ulinc_config)
        if refresh_ulinc_campaigns(ulinc_config):
            return jsonify({"message": "success"})
        else:
            return make_response(jsonify({"message": "Failure: unable to refresh ulinc campaigns"}), 300) # Should try again
    else:
        return make_response(jsonify({"message": "Failure: ulinc credentials are likely incorrect"}), 200) # Task should not repeat

@mod_tasks.route('/data_enrichment', methods=['POST'])
def data_enrichment_task():
    """
    Required JSON keys: contact_id
    """
    json_body = request.get_json(force=True)
    contact = db.session.query(Contact).filter(Contact.contact_id == json_body['contact_id']).first()

    if data_enrichment_function(contact) == 'success':
        return jsonify({"message": "success"})
    return make_response(jsonify({"message": "failure"}), 300) # Task should repeat

@mod_tasks.route('/send_email', methods=['POST'])
def send_email_task():
    """
    Required JSON keys: email_target_details
    """
    json_body = request.get_json(force=True)

    if email_config := db.session.query(Email_config).filter(Email_config.email_config_id == json_body['email_target_details']['email_config_id']).first():
        if contact := db.session.query(Contact.contact_id == json_body['email_target_details']['contact_id']).first():
            if contact.is_messaging_task_valid():
                send_email_function(email_config, json_body['email_target_details'])
                return jsonify({"message": "success"})
            return jsonify({"message": "Messaging task no longer valid"})
        return jsonify({"message": "Unknown contact_id"})
    else:
        return jsonify({"message": "Failure. Email config does not exist"}) # Should not repeat

@mod_tasks.route('/send_li_message', methods=['POST'])
def send_li_message_task():
    """
    Required JSON keys: li_message_target_details
    """
    json_body = request.get_json(force=True)

    if contact := db.session.query(Contact.contact_id == json_body['li_message_target_details']['contact_id']).first():
        if contact.is_messaging_task_valid():
            if send_li_message_function(json_body['li_message_target_details']) == 'Message sent':
                gct_client = google_tasks.create_tasks_client()
                payload = {
                    'li_message_target_details': json_body['li_message_target_details'],
                }
                if os.getenv('FLASK_ENV') == 'production':
                    gct_parent = google_tasks.create_tasks_parent(gct_client, os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), 'update-ulinc-contact-status')
                    task = google_tasks.create_app_engine_task('/api/v1/tasks/update_ulinc_contact_status', payload)
                else:
                    gct_parent = google_tasks.create_tasks_parent(gct_client, 'foundation-staging-305217', 'us-central1', 'update-ulinc-contact-status')
                    task = google_tasks.create_url_task(os.getenv("BACKEND_API_URL"), '/api/v1/tasks/update_ulinc_contact_status', payload)
                task_response = google_tasks.send_task(gct_client, gct_parent, task)
                return jsonify({"message": "success"})
            return make_response(jsonify({"message": "failure"}), 300) # Task should repeat
        return jsonify({"message": "Messaging task no longer valid"})
    return jsonify({"message": "Unknown contact_id"})

@mod_tasks.route('/update_ulinc_contact_status', methods=['POST'])
def update_ulinc_contact_status_task():
    """
    Required JSON keys: li_message_target_details
    """
    json_body = request.get_json(force=True)
    if update_ulinc_contact_status(json_body['li_message_target_details']) == "Ulinc contact updated":
        return jsonify({"message": "success"})
    return make_response(jsonify({"message": "failure"}), 300) # Task should repeat
