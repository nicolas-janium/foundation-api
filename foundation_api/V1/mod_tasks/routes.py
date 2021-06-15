from datetime import datetime
import logging

from flask import Blueprint, jsonify, request
from sqlalchemy import and_

from foundation_api.V1.sa_db.model import db
from foundation_api.V1.sa_db.model import Account, Ulinc_config, Contact_source
from foundation_api.V1.utils.data_enrichment import data_enrichment_function
from foundation_api.V1.utils.refresh_ulinc_data import refresh_ulinc_campaigns, refresh_ulinc_cookie
from foundation_api.V1.utils.poll_ulinc_webhook import poll_ulinc_webhooks, poll_and_save_webhook
from foundation_api.V1.utils.poll_ulinc_csv import handle_csv_data, poll_and_save_csv
from foundation_api.V1.utils.process_contact_source_handler import process_contact_source_function
from foundation_api.V1.utils.send_email import send_email_function
from foundation_api.V1.utils.send_li_message import send_li_message_function
from foundation_api.V1.utils.ses import send_simple_email


logger = logging.getLogger('api_tasks')
formatter = logging.Formatter('%(levelname)s - %(message)s')
logHandler = logging.StreamHandler()
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

mod_tasks = Blueprint('tasks', __name__, url_prefix='/api/v1/tasks')

@mod_tasks.route('/poll_ulinc_webhooks', methods=['GET'])
def poll_ulinc_webhooks_route_function():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()

    fail_list = []
    success_list = []
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id:
                try:
                    poll_and_save_webhook(account, ulinc_config.new_connection_webhook, 1)
                    poll_and_save_webhook(account, ulinc_config.new_message_webhook, 2)
                    poll_and_save_webhook(account, ulinc_config.send_message_webhook, 3)
                    success_list.append(account.account_id)
                except Exception as err:
                    logger.error("Poll Ulinc webhook error for account {}: {}".format(account.account_id, err))
                    fail_list.append({"account_id": account.account_id, "ulinc_config_id": ulinc_config.ulinc_config_id})
    # Send email to nic@janium.io
    task_summary = {"poll_ulinc_webhook_fail_list": fail_list, "poll_ulinc_webhook_success_list": success_list}
    # send_simple_email('nic@janium.io', json.dumps(task_summary), "Poll Ulinc Task Summary")
    return jsonify(task_summary)

@mod_tasks.route('/poll_ulinc_csv', methods=['GET'])
def poll_ulinc_csv_route_function():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        and_(Account.data_enrichment_start_date < datetime.utcnow(), Account.data_enrichment_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()

    fail_list = []
    success_list = []
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            campaign_success_list = []
            campaign_fail_list = []
            if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id:
                for ulinc_campaign in ulinc_config.ulinc_campaigns:
                    try:
                        if poll_and_save_csv(ulinc_config, ulinc_campaign):
                            campaign_success_list.append(ulinc_campaign.ulinc_campaign_id)
                        else:
                            campaign_fail_list.append(ulinc_campaign.ulinc_campaign_id)
                    except Exception as err:
                        logger.error("Poll Ulinc csv error for ulinc_campaign {}: {}".format(ulinc_campaign.ulinc_campaign_id, err))
                        campaign_fail_list.append(ulinc_campaign.ulinc_campaign_id)

                fail_list.append({"account_id": account.account_id, "ulinc_config_id": ulinc_config.ulinc_config_id, "ulinc_campaigns": campaign_fail_list})
                success_list.append({"account_id": account.account_id, "ulinc_config_id": ulinc_config.ulinc_config_id, "ulinc_campaigns": campaign_success_list})
    return jsonify({"poll_ulinc_csv_fail_list": fail_list if campaign_fail_list else [], "poll_ulinc_csv_success_list": success_list})

@mod_tasks.route('/process_contact_source', methods=['POST'])
def process_contact_source():
    """
    Required JSON keys: account_id, ulinc_config_id, contact_source_id
    """
    json_body = request.get_json(force=True)
    account = db.session.query(Account).filter(Account.account_id == json_body['account_id']).first()
    ulinc_config = db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first()
    contact_source = db.session.query(Contact_source).filter(Contact_source.contact_source_id == json_body['contact_source_id']).first()
    
    return process_contact_source_function(account, ulinc_config, contact_source)