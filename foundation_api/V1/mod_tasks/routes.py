from datetime import datetime, timedelta, timezone
from uuid import uuid4
import logging
from functools import wraps

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import and_, or_

from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_tasks.models import Account, Ulinc_config
from foundation_api.V1.utils.data_enrichment import data_enrichment_function
from foundation_api.V1.utils.refresh_ulinc_data import refresh_ulinc_campaigns, refresh_ulinc_cookie
from foundation_api.V1.utils.poll_ulinc_webhook import poll_ulinc_webhooks
from foundation_api.V1.utils.poll_ulinc_csv import handle_csv_data

logger = logging.getLogger('api_tasks')
formatter = logging.Formatter('%(levelname)s - %(message)s')
logHandler = logging.StreamHandler()
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

mod_tasks = Blueprint('tasks', __name__, url_prefix='/api/v1/tasks')

def check_cron_header(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if cron_header := request.headers.get('X-Appengine-Cron'):
            return f(*args, **kwargs)
        return make_response(jsonify({"message": "Missing X-Appengine-Cron header"}), 400)
    return decorated

@mod_tasks.route('/poll_ulinc_webhooks', methods=['GET'])
@check_cron_header
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
                    poll_ulinc_webhooks(account, ulinc_config)
                    success_list.append(account.account_id)
                except Exception as err:
                    logger.error("Poll Ulinc webhook error for account {}: {}".format(account.account_id, err))
    return jsonify({"poll_ulinc_webhook_fail_list": fail_list, "poll_ulinc_webhook_success_list": success_list})

@mod_tasks.route('/poll_ulinc_csv', methods=['GET'])
@check_cron_header
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
            if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id:
                try:
                    handle_csv_data(account, ulinc_config)
                    
                    success_list.append(account.account_id)
                except Exception as err:
                    logger.error("Poll Ulinc csv error for account {}: {}".format(account.account_id, err))
    return jsonify({"poll_ulinc_csv_fail_list": fail_list, "poll_ulinc_csv_success_list": success_list})


@mod_tasks.route('/refresh_ulinc_data', methods=['GET'])
@check_cron_header
def refresh_ulinc_data():
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
                    refresh_ulinc_cookie(ulinc_config)
                    refresh_ulinc_campaigns(account, ulinc_config)
                    success_list.append(account.account_id)
                except Exception as err:
                    logger.error("Refresh Ulinc data error for account {}: {}".format(account.account_id, err))
                    fail_list.append({"account_id": account.account_id, "ulinc_config_id": ulinc_config.ulinc_config_id})
    return jsonify({"refresh_ulinc_data_fail_list": fail_list, "refresh_ulinc_data_success_list": success_list})

@mod_tasks.route('/data_enrichment', methods=['GET'])
@check_cron_header
def data_enrichment():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        and_(Account.data_enrichment_start_date < datetime.utcnow(), Account.data_enrichment_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()

    fail_list = []
    enriched_list = []
    for account in accounts:
        try:
            enriched_list.append(
                {
                    "account_id": account.account_id,
                    "enriched_contacts": data_enrichment_function(account)
                }
            )
        except Exception as err:
            logger.error("Data Enrichment error for account {}: {}".format(account.account_id, err))
            fail_list.append({"account_id": account.account_id})
    return jsonify({"data_enrichment_fail_list": fail_list, "data_enrichment_success_list": enriched_list})
