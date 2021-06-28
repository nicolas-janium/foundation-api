from datetime import datetime
import logging

from flask import Blueprint, jsonify, request, make_response
from sqlalchemy import and_

from foundation_api.V1.sa_db.model import db
from foundation_api.V1.sa_db.model import Account, Ulinc_config, Contact_source, Ulinc_campaign, Janium_campaign, Contact
from foundation_api.V1.utils.refresh_ulinc_data import refresh_ulinc_campaigns, refresh_ulinc_cookie
from foundation_api.V1.utils.poll_ulinc_webhook import poll_and_save_webhook
from foundation_api.V1.utils.poll_ulinc_csv import poll_and_save_csv
from foundation_api.V1.utils.process_contact_source_handler import process_contact_source_function
from foundation_api.V1.utils.data_enrichment import data_enrichment_function


logger = logging.getLogger('api_tasks')
formatter = logging.Formatter('%(levelname)s - %(message)s')
logHandler = logging.StreamHandler()
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

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
    
    if process_contact_source_function(account, ulinc_config, contact_source):
        return jsonify({"message": "success"})
    return make_response(jsonify({"message": "failure"}), 300)

@mod_tasks.route('/refresh_ulinc_data', methods=['POST'])
def refresh_ulinc_data_task():
    """
    Required JSON keys: ulinc_config_id
    """
    json_body = request.get_json(force=True)
    ulinc_config = db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first()
    
    refresh_ulinc_cookie(ulinc_config)
    if ulinc_config.is_working:
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

