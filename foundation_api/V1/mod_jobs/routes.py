from datetime import datetime, timedelta
import logging
from functools import wraps
import json
import os
from pprint import pprint

from flask import Blueprint, jsonify, request, make_response, current_app
from sqlalchemy import and_
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from foundation_api.V1.sa_db.model import Contact_source, get_db_session
from foundation_api.V1.sa_db.model import Account, Ulinc_config


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
        elif postman_header := request.headers.get('Postman-Token'):
            return f(*args, **kwargs)
        return make_response(jsonify({"message": "Missing X-Appengine-Cron header"}), 400)
    return decorated

@mod_jobs.route('/poll_ulinc_webhooks', methods=['GET'])
@check_cron_header
def poll_ulinc_webhooks_job():
    with get_db_session() as session:
        accounts = session.query(Account).filter(
            and_(
                and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
                and_(Account.payment_effective_start_date < datetime.utcnow(), Account.payment_effective_end_date > datetime.utcnow()),
                Account.is_polling_ulinc == 1,
                Account.account_id != Account.unassigned_account_id
            )
        ).all()

        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id and ulinc_config.ulinc_is_active and ulinc_config.is_working:
                    for webhook in ulinc_config.get_webhooks():
                        payload = {
                            'ulinc_config_id': ulinc_config.ulinc_config_id,
                            'webhook_url': webhook['url'],
                            'webhook_type': webhook['type']
                        }
                        if os.getenv('FLASK_ENV') == 'production':
                            parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='poll-ulinc-webhook')
                            task = {
                                'app_engine_http_request': {
                                    'http_method': tasks_v2.HttpMethod.POST,
                                    'relative_uri': '/api/v1/tasks/poll_ulinc_webhook',
                                    'body': json.dumps(payload).encode(),
                                    'headers': {
                                        'Content-type': 'application/json'
                                    }
                                }
                            }
                        else:
                            parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='poll-ulinc-webhook')
                            task = {
                                "http_request": {  # Specify the type of request.
                                    "http_method": tasks_v2.HttpMethod.POST,
                                    "url": "{}/api/v1/tasks/poll_ulinc_webhook".format(os.getenv("BACKEND_API_URL")),
                                    'body': json.dumps(payload).encode(),
                                    'headers': {
                                        'Content-type': 'application/json'
                                    }
                                }
                            }
                        task_response = gc_tasks_client.create_task(parent=parent, task=task)
                        tasks.append({
                            "account_id": account.account_id,
                            "ulinc_config_id": ulinc_config.ulinc_config_id,
                            "task_id": task_response.name,
                            "webhook_url": webhook['url'],
                            "webhook_type": webhook['type']
                        })
    return jsonify(tasks)

@mod_jobs.route('/poll_ulinc_csv', methods=['GET'])
@check_cron_header
def poll_ulinc_csv_job():
    with get_db_session() as session:
        accounts = session.query(Account).filter(and_(
            and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
            and_(Account.data_enrichment_start_date < datetime.utcnow(), Account.data_enrichment_end_date > datetime.utcnow()),
            and_(Account.payment_effective_start_date < datetime.utcnow(), Account.payment_effective_end_date > datetime.utcnow()),
            Account.is_polling_ulinc == 1,
            Account.account_id != Account.unassigned_account_id
        )).all()

        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id and ulinc_config.ulinc_is_active and ulinc_config.is_working:
                    for ulinc_campaign in ulinc_config.ulinc_campaigns:
                        payload = {
                            'ulinc_config_id': ulinc_config.ulinc_config_id,
                            'ulinc_campaign_id': ulinc_campaign.ulinc_campaign_id
                        }
                        if os.getenv('FLASK_ENV') == 'production':
                            parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='poll-ulinc-csv')
                            task = {
                                'app_engine_http_request': {
                                    'http_method': tasks_v2.HttpMethod.POST,
                                    'relative_uri': '/api/v1/tasks/poll_ulinc_csv',
                                    'body': json.dumps(payload).encode(),
                                    'headers': {
                                        'Content-type': 'application/json'
                                    }
                                }
                            }
                        else:
                            parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='poll-ulinc-csv')
                            task = {
                                "http_request": {  # Specify the type of request.
                                    "http_method": tasks_v2.HttpMethod.POST,
                                    "url": "{}/api/v1/tasks/poll_ulinc_csv".format(os.getenv("BACKEND_API_URL")),
                                    'body': json.dumps(payload).encode(),
                                    'headers': {
                                        'Content-type': 'application/json'
                                    }
                                }
                            }
                        task_response = gc_tasks_client.create_task(parent=parent, task=task)
                        tasks.append({
                            "account_id": account.account_id,
                            "ulinc_config_id": ulinc_config.ulinc_config_id,
                            "task_id": task_response.name,
                            "ulinc_campaign_id": ulinc_campaign.ulinc_campaign_id
                        })
    return jsonify(tasks)

@mod_jobs.route('/process_contact_sources', methods=['GET'])
@check_cron_header
def process_contact_sources_job():
    with get_db_session() as session:
        accounts = session.query(Account).filter(and_(
            and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
            and_(Account.payment_effective_start_date < datetime.utcnow(), Account.payment_effective_end_date > datetime.utcnow()),
            Account.is_polling_ulinc == 1,
            Account.account_id != Account.unassigned_account_id
        )).all()
        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                for i, contact_source in enumerate(ulinc_config.contact_sources.filter(Contact_source.is_processed == 0).order_by(Contact_source.contact_source_type_id.asc()).all()):    
                    payload = {
                        'account_id': account.account_id,
                        'ulinc_config_id': ulinc_config.ulinc_config_id,
                        'contact_source_id': contact_source.contact_source_id
                    }
                    if os.getenv('FLASK_ENV') == 'production':
                        parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='process-cs-queue')
                        task = {
                            'app_engine_http_request': {
                                'http_method': tasks_v2.HttpMethod.POST,
                                'relative_uri': '/api/v1/tasks/process_contact_source',
                                'body': json.dumps(payload).encode(),
                                'headers': {
                                    'Content-type': 'application/json'
                                }
                            }
                        }
                    else:
                        parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='process-cs-queue')
                        task = {
                            "http_request": {  # Specify the type of request.
                                "http_method": tasks_v2.HttpMethod.POST,
                                "url": "{}/api/v1/tasks/process_contact_source".format(os.getenv("BACKEND_API_URL")),
                                'body': json.dumps(payload).encode(),
                                'headers': {
                                    'Content-type': 'application/json'
                                }
                            }
                        }

                    # Create Timestamp protobuf.
                    timestamp = timestamp_pb2.Timestamp()
                    timestamp.FromDatetime(datetime.utcnow() + timedelta(seconds=(i * 10)))
                    task['schedule_time'] = timestamp

                    task_response = gc_tasks_client.create_task(parent=parent, task=task)
                    tasks.append({
                        "account_id": account.account_id,
                        "ulinc_config_id": ulinc_config.ulinc_config_id,
                        "task_id": task_response.name,
                        "contact_source_id": contact_source.contact_source_id
                    })
    return jsonify(tasks)

@mod_jobs.route('/refresh_ulinc_data', methods=['GET'])
@check_cron_header
def refresh_ulinc_data():
    with get_db_session() as session:
        accounts = session.query(Account).filter(and_(
            and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
            and_(Account.payment_effective_start_date < datetime.utcnow(), Account.payment_effective_end_date > datetime.utcnow()),
            Account.account_id != Account.unassigned_account_id
        )).all()
        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id:
                    payload = {
                        'ulinc_config_id': ulinc_config.ulinc_config_id,
                    }
                    if os.getenv('FLASK_ENV') == 'production':
                        parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='refresh-ulinc-data')
                        task = {
                            'app_engine_http_request': {
                                'http_method': tasks_v2.HttpMethod.POST,
                                'relative_uri': '/api/v1/tasks/refresh_ulinc_data',
                                'body': json.dumps(payload).encode(),
                                'headers': {
                                    'Content-type': 'application/json'
                                }
                            }
                        }
                    else:
                        parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='refresh-ulinc-data')
                        task = {
                            "http_request": {  # Specify the type of request.
                                "http_method": tasks_v2.HttpMethod.POST,
                                "url": "{}/api/v1/tasks/refresh_ulinc_data".format(os.getenv("BACKEND_API_URL")),
                                'body': json.dumps(payload).encode(),
                                'headers': {
                                    'Content-type': 'application/json'
                                }
                            }
                        }
                    task_response = gc_tasks_client.create_task(parent=parent, task=task)
                    tasks.append({
                        "account_id": account.account_id,
                        "ulinc_config_id": ulinc_config.ulinc_config_id,
                        "task_id": task_response.name
                    })
    return jsonify(tasks)

@mod_jobs.route('/data_enrichment', methods=['GET'])
@check_cron_header
def data_enrichment_job():
    with get_db_session() as session:
        accounts = session.query(Account).filter(and_(
            and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
            and_(Account.payment_effective_start_date < datetime.utcnow(), Account.payment_effective_end_date > datetime.utcnow()),
            and_(Account.data_enrichment_start_date < datetime.utcnow(), Account.data_enrichment_end_date > datetime.utcnow()),
            Account.account_id != Account.unassigned_account_id
        )).all()
        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                for janium_campaign in ulinc_config.janium_campaigns:
                    contacts  = janium_campaign.get_data_enrichment_targets()
                    for contact in contacts:
                        payload = {
                            'contact_id': contact.contact_id,
                        }
                        if os.getenv('FLASK_ENV') == 'production':
                            parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='data-enrichment')
                            task = {
                                'app_engine_http_request': {
                                    'http_method': tasks_v2.HttpMethod.POST,
                                    'relative_uri': '/api/v1/tasks/data_enrichment',
                                    'body': json.dumps(payload).encode(),
                                    'headers': {
                                        'Content-type': 'application/json'
                                    }
                                }
                            }
                        else:
                            parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='data-enrichment')
                            task = {
                                "http_request": {  # Specify the type of request.
                                    "http_method": tasks_v2.HttpMethod.POST,
                                    "url": "{}/api/v1/tasks/data_enrichment".format(os.getenv("BACKEND_API_URL")),
                                    'body': json.dumps(payload).encode(),
                                    'headers': {
                                        'Content-type': 'application/json'
                                    }
                                }
                            }
                        task_response = gc_tasks_client.create_task(parent=parent, task=task)
                        tasks.append({
                            "account_id": account.account_id,
                            "ulinc_config_id": ulinc_config.ulinc_config_id,
                            "janium_campaign_id": janium_campaign.janium_campaign_id,
                            "contact_id": contact.contact_id,
                            "task_id": task_response.name
                        })
    return jsonify(tasks)

@mod_jobs.route('/send_email', methods=['GET'])
@check_cron_header
def send_email():
    with get_db_session() as session:
        accounts = session.query(Account).filter(and_(
            and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
            and_(Account.payment_effective_start_date < datetime.utcnow(), Account.payment_effective_end_date > datetime.utcnow()),
            Account.is_sending_emails == 1,
            Account.account_id != Account.unassigned_account_id
        )).all()

        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                for janium_campaign in ulinc_config.janium_campaigns:
                    # Generate the timestamp to be used in task
                    if scheduled_timestamp := janium_campaign.generate_random_timestamp_in_queue_interval():
                        # Create Timestamp protobuf
                        timestamp = timestamp_pb2.Timestamp()
                        timestamp.FromDatetime(scheduled_timestamp)

                        for target in janium_campaign.get_email_targets():
                            payload = {
                                'email_target_details': target,
                            }
                            if os.getenv('FLASK_ENV') == 'production':
                                parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send_email')
                                task = {
                                    'app_engine_http_request': {
                                        'http_method': tasks_v2.HttpMethod.POST,
                                        'relative_uri': '/api/v1/tasks/send_email',
                                        'body': json.dumps(payload).encode(),
                                        'headers': {
                                            'Content-type': 'application/json'
                                        }
                                    }
                                }
                            else:
                                parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send_email')
                                task = {
                                    "http_request": {  # Specify the type of request.
                                        "http_method": tasks_v2.HttpMethod.POST,
                                        "url": "{}/api/v1/tasks/send_email".format(os.getenv("BACKEND_API_URL")),
                                        'body': json.dumps(payload).encode(),
                                        'headers': {
                                            'Content-type': 'application/json'
                                        }
                                    }
                                }

                            # Add the timestamp to the tasks.
                            task['schedule_time'] = timestamp

                            task_response = gc_tasks_client.create_task(parent=parent, task=task)
                            tasks.append({
                                "account_id": account.account_id,
                                "ulinc_config_id": ulinc_config.ulinc_config_id,
                                "janium_campaign_id": janium_campaign.janium_campaign_id,
                                "email_target_details": target,
                                "task_id": task_response.name,
                                "scheduled_time": scheduled_timestamp
                            })
                            # break
    return jsonify(tasks)

@mod_jobs.route('/send_li_message', methods=['GET'])
@check_cron_header
def send_li_message_job():
    with get_db_session() as session:
        accounts = session.query(Account).filter(and_(
            and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
            and_(Account.payment_effective_start_date < datetime.utcnow(), Account.payment_effective_end_date > datetime.utcnow()),
            Account.is_sending_li_messages == 1,
            Account.account_id != Account.unassigned_account_id
        )).all()

        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                for janium_campaign in ulinc_config.janium_campaigns:
                    # Generate the timestamp to be used in task
                    if scheduled_timestamp := janium_campaign.generate_random_timestamp_in_queue_interval() and ulinc_config.ulinc_is_active and ulinc_config.is_working:
                        # Create Timestamp protobuf
                        timestamp = timestamp_pb2.Timestamp()
                        timestamp.FromDatetime(scheduled_timestamp)

                        for target in janium_campaign.get_li_message_targets():
                            payload = {
                                'li_message_target_details': target,
                            }
                            if os.getenv('FLASK_ENV') == 'production':
                                parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send_li_message')
                                task = {
                                    'app_engine_http_request': {
                                        'http_method': tasks_v2.HttpMethod.POST,
                                        'relative_uri': '/api/v1/tasks/send_li_message',
                                        'body': json.dumps(payload).encode(),
                                        'headers': {
                                            'Content-type': 'application/json'
                                        }
                                    }
                                }
                            else:
                                parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send_li_message')
                                task = {
                                    "http_request": {  # Specify the type of request.
                                        "http_method": tasks_v2.HttpMethod.POST,
                                        "url": "{}/api/v1/tasks/send_li_message".format(os.getenv("BACKEND_API_URL")),
                                        'body': json.dumps(payload).encode(),
                                        'headers': {
                                            'Content-type': 'application/json'
                                        }
                                    }
                                }

                            # Add the timestamp to the tasks.
                            task['schedule_time'] = timestamp

                            task_response = gc_tasks_client.create_task(parent=parent, task=task)
                            tasks.append({
                                "account_id": account.account_id,
                                "ulinc_config_id": ulinc_config.ulinc_config_id,
                                "janium_campaign_id": janium_campaign.janium_campaign_id,
                                "email_target_details": target,
                                "task_id": task_response.name,
                                "scheduled_time": scheduled_timestamp
                            })
                            # break
    return jsonify(tasks)
