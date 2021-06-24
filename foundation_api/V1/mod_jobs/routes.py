from datetime import datetime
import logging
from functools import wraps
import pytz
import json
import os

from flask import Blueprint, jsonify, request, make_response
from sqlalchemy import and_
from google.cloud import tasks_v2

from foundation_api.V1.sa_db.model import Contact_source, db
from foundation_api.V1.sa_db.model import Account, Ulinc_config
from foundation_api.V1.utils.data_enrichment import data_enrichment_function
from foundation_api.V1.utils.refresh_ulinc_data import refresh_ulinc_campaigns, refresh_ulinc_cookie
from foundation_api.V1.utils.poll_ulinc_webhook import poll_ulinc_webhooks, poll_and_save_webhook
from foundation_api.V1.utils.poll_ulinc_csv import handle_csv_data, poll_and_save_csv
from foundation_api.V1.utils.process_contact_source_handler import process_contact_source_function
from foundation_api.V1.utils.send_email import send_email_function
from foundation_api.V1.utils.send_li_message import send_li_message_function
from foundation_api.V1.utils.ses import send_simple_email


logger = logging.getLogger('api_jobs')
formatter = logging.Formatter('%(levelname)s - %(message)s')
logHandler = logging.StreamHandler()
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

gc_tasks_client = tasks_v2.CloudTasksClient()

mod_jobs = Blueprint('jobs', __name__, url_prefix='/api/v1/jobs')

def check_cron_header(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if cron_header := request.headers.get('X-Appengine-Cron'):
            return f(*args, **kwargs)
        return make_response(jsonify({"message": "Missing X-Appengine-Cron header"}), 400)
    return decorated

@mod_jobs.route('/poll_ulinc_webhooks', methods=['GET'])
@check_cron_header
def poll_ulinc_webhooks_job():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()

    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id:
                for webhook in ulinc_config.get_webhooks():
                    # parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), 'us-central1', queue='process-cs-queue')
                    parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='poll-ulinc-webhook')
                    payload = {
                        'ulinc_config_id': ulinc_config.ulinc_config_id,
                        'webhook_url': webhook['url'],
                        'webhook_type': webhook['type']
                        
                    }
                    task = {
                        "http_request": {  # Specify the type of request.
                            "http_method": tasks_v2.HttpMethod.POST,
                            "url": "https://a40504218726.ngrok.io/api/v1/tasks/poll_ulinc_webhook",
                            'body': json.dumps(payload).encode(),
                            'headers': {
                                'Content-type': 'application/json'
                            }
                        }
                    }
                    # task = {
                    #     'app_engine_http_request': {
                    #         'http_method': tasks_v2.HttpMethod.POST,
                    #         'relative_uri': '/tasks/process_contact_source',
                    #         'body': json.dumps(payload).encode(),
                    #         'headers': {
                    #             'Content-type': 'application/json'
                    #         }
                    #     }
                    # }
                    task_response = gc_tasks_client.create_task(parent=parent, task=task)
    return jsonify([])

@mod_jobs.route('/poll_ulinc_csv', methods=['GET'])
@check_cron_header
def poll_ulinc_csv_job():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        and_(Account.data_enrichment_start_date < datetime.utcnow(), Account.data_enrichment_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()

    # fail_list = []
    # success_list = []
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            # campaign_success_list = []
            # campaign_fail_list = []
            if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id:
                for ulinc_campaign in ulinc_config.ulinc_campaigns:
                    # parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), 'us-central1', queue='process-cs-queue')
                    parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='poll-ulinc-csv')
                    payload = {
                        'ulinc_config_id': ulinc_config.ulinc_config_id,
                        'ulinc_campaign_id': ulinc_campaign.ulinc_campaign_id
                    }
                    task = {
                        "http_request": {  # Specify the type of request.
                            "http_method": tasks_v2.HttpMethod.POST,
                            "url": "https://a40504218726.ngrok.io/api/v1/tasks/poll_ulinc_csv",
                            'body': json.dumps(payload).encode(),
                            'headers': {
                                'Content-type': 'application/json'
                            }
                        }
                    }
                    # task = {
                    #     'app_engine_http_request': {
                    #         'http_method': tasks_v2.HttpMethod.POST,
                    #         'relative_uri': '/tasks/process_contact_source',
                    #         'body': json.dumps(payload).encode(),
                    #         'headers': {
                    #             'Content-type': 'application/json'
                    #         }
                    #     }
                    # }
                    task_response = gc_tasks_client.create_task(parent=parent, task=task)
                # for ulinc_campaign in ulinc_config.ulinc_campaigns:
                #     if contact_source_id := poll_and_save_csv(ulinc_config, ulinc_campaign):
                #         campaign_success_list.append(ulinc_campaign.ulinc_campaign_id)
                #     else:
                #         campaign_fail_list.append(ulinc_campaign.ulinc_campaign_id)
                # fail_list.append({"account_id": account.account_id, "ulinc_config_id": ulinc_config.ulinc_config_id, "ulinc_campaigns": campaign_fail_list})
                # success_list.append({"account_id": account.account_id, "ulinc_config_id": ulinc_config.ulinc_config_id, "ulinc_campaigns": campaign_success_list})
    # return jsonify({"poll_ulinc_csv_fail_list": fail_list if campaign_fail_list else [], "poll_ulinc_csv_success_list": success_list})
    return jsonify([])

@mod_jobs.route('/process_contact_sources', methods=['GET'])
@check_cron_header
def process_contact_sources_job():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            for contact_source in ulinc_config.contact_sources.filter(Contact_source.is_processed == 0).all():
                # parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), 'us-central1', queue='process-cs-queue')
                parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='process-cs-queue')
                payload = {
                    'account_id': account.account_id,
                    'ulinc_config_id': ulinc_config.ulinc_config_id,
                    'contact_source_id': contact_source.contact_source_id
                }
                task = {
                    "http_request": {  # Specify the type of request.
                        "http_method": tasks_v2.HttpMethod.POST,
                        "url": "https://a40504218726.ngrok.io/api/v1/tasks/process_contact_source",
                        'body': json.dumps(payload).encode(),
                        'headers': {
                            'Content-type': 'application/json'
                        }
                    }
                }
                # task = {
                #     'app_engine_http_request': {
                #         'http_method': tasks_v2.HttpMethod.POST,
                #         'relative_uri': '/tasks/process_contact_source',
                #         'body': json.dumps(payload).encode(),
                #         'headers': {
                #             'Content-type': 'application/json'
                #         }
                #     }
                # }
                task_response = gc_tasks_client.create_task(parent=parent, task=task)

    return jsonify([])

@mod_jobs.route('/refresh_ulinc_data', methods=['GET'])
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
                refresh_ulinc_cookie(ulinc_config)
                if ulinc_config.is_working:
                    refresh_ulinc_campaigns(account, ulinc_config)
                    success_list.append(account.account_id)
                else:
                    fail_list.append({"account_id": account.account_id, "ulinc_config_id": ulinc_config.ulinc_config_id})
    return jsonify({"refresh_ulinc_data_fail_list": fail_list, "refresh_ulinc_data_success_list": success_list})

@mod_jobs.route('/data_enrichment', methods=['GET'])
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

@mod_jobs.route('/send_email', methods=['GET'])
@check_cron_header
def send_email():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id,
        Account.is_sending_emails
    )).all()

    fail_list = []
    success_list = []
    for account in accounts:
        account_local_time = datetime.now(pytz.timezone('UTC')).astimezone(pytz.timezone(account.time_zone.time_zone_code)).replace(tzinfo=None)
        for janium_campaign in account.janium_campaigns:
            effective_dates_dict = janium_campaign.get_effective_dates(account.time_zone.time_zone_code)
            queue_times_dict = janium_campaign.get_queue_times(account.time_zone.time_zone_code)
            # if (effective_dates_dict['start'] <= account_local_time <= effective_dates_dict['end']) and (queue_times_dict['start'].hour <= account_local_time.hour <= queue_times_dict['end'].hour):
            if (effective_dates_dict['start'] <= account_local_time <= effective_dates_dict['end']) and (queue_times_dict['start'].hour <= account_local_time.hour <= 23):
                try:
                    task_res = send_email_function(account, janium_campaign, account_local_time, queue_times_dict)
                    success_list.append({"account_id": account.account_id, "janium_campaign_id": janium_campaign.janium_campaign_id, "email_recipients": task_res})
                except Exception as err:
                    logger.error("Send email error for account {}: {}".format(account.account_id, err))
                    fail_list.append({"account_id": account.account_id})
    return jsonify({"send_email_fail_list": fail_list, "send_email_success_list": success_list})

@mod_jobs.route('/send_li_message', methods=['GET'])
@check_cron_header
def send_li_message():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id,
        Account.is_sending_li_messages
    )).all()

    fail_list = []
    success_list = []
    for account in accounts:
        account_local_time = datetime.now(pytz.timezone('UTC')).astimezone(pytz.timezone(account.time_zone.time_zone_code)).replace(tzinfo=None)
        for ulinc_config in account.ulinc_configs:
            for janium_campaign in ulinc_config.janium_campaigns:
                effective_dates_dict = janium_campaign.get_effective_dates(account.time_zone.time_zone_code)
                queue_times_dict = janium_campaign.get_queue_times(account.time_zone.time_zone_code)
                if (effective_dates_dict['start'] <= account_local_time <= effective_dates_dict['end']) and (queue_times_dict['start'].hour <= account_local_time.hour <= queue_times_dict['end'].hour):
                    try:
                        task_res = send_li_message_function(account, ulinc_config, janium_campaign, account_local_time, queue_times_dict)
                        success_list.append({"account_id": account.account_id, "janium_campaign_id": janium_campaign.janium_campaign_id, "li_message_recipients": task_res})
                    except Exception as err:
                        logger.error("Send LI message error for account {}: {}".format(account.account_id, err))
                        fail_list.append({"account_id": account.account_id})
    return jsonify({"send_li_message_fail_list": fail_list, "send_li_message_success_list": success_list})
