# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import logging
from functools import wraps
import json
import os
from pprint import pprint

from flask import Blueprint, jsonify, request, make_response, current_app
from google.cloud.tasks_v2.services.cloud_tasks.pagers import ListTasksAsyncPager
from sqlalchemy import and_
from sqlalchemy.orm import defer, undefer
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from foundation_api.V1.sa_db.model import Contact_source, get_db_session
from foundation_api.V1.sa_db.model import Account, Ulinc_config, Cookie
from foundation_api.V1.utils.google_tasks import get_tasks


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
                        task = {
                            "http_request": {  # Specify the type of request.
                                "http_method": tasks_v2.HttpMethod.POST,
                                "url": os.getenv('POLL_ULINC_WEBHOOK_TASK_HANDLER_URL'),
                                'body': json.dumps(payload).encode(),
                                'headers': {
                                    'Content-type': 'application/json'
                                }
                            }
                        }
                        queue = 'poll-ulinc-webhook'
                        if os.getenv('FLASK_ENV') == 'production':
                            parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue=queue)
                            
                        else:
                            parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue=queue)

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
                        task = {
                            "http_request": {  # Specify the type of request.
                                "http_method": tasks_v2.HttpMethod.POST,
                                "url": os.getenv('POLL_ULINC_CSV_TASK_HANDLER_URL'),
                                'body': json.dumps(payload).encode(),
                                'headers': {
                                    'Content-type': 'application/json'
                                }
                            }
                        }
                        queue = 'poll-ulinc-csv'
                        if os.getenv('FLASK_ENV') == 'production':
                            parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue=queue)
                            
                        else:
                            parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue=queue)

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
                for i, contact_source in enumerate(ulinc_config.contact_sources.filter(Contact_source.is_processed == 0).options(defer('contact_source_json')).order_by(Contact_source.contact_source_type_id.asc()).all()):    
                    payload = {
                        'account_id': account.account_id,
                        'ulinc_config_id': ulinc_config.ulinc_config_id,
                        'contact_source_id': contact_source.contact_source_id
                    }
                    task = {
                        "http_request": {  # Specify the type of request.
                            "http_method": tasks_v2.HttpMethod.POST,
                            "url": os.getenv('PROCESS_CONTACT_SOURCE_TASK_HANDLER_URL'),
                            'body': json.dumps(payload).encode(),
                            'headers': {
                                'Content-type': 'application/json'
                            }
                        }
                    }
                    queue = 'process-cs-queue'
                    if os.getenv('FLASK_ENV') == 'production':
                        parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue=queue)
                        
                    else:
                        parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue=queue)

                    list_tasks_request = tasks_v2.ListTasksRequest()
                    list_tasks_request.parent = parent
                    list_tasks_request.response_view = 2
                    existing_tasks = gc_tasks_client.list_tasks(list_tasks_request)
                    existing_contact_source_ids = [json.loads(task.http_request.body)['contact_source_id'] for task in existing_tasks]

                    if contact_source.contact_source_id in existing_contact_source_ids:
                        continue

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

@mod_jobs.route('/refresh_ulinc_cookie', methods=['GET'])
@check_cron_header
def refresh_ulinc_cookie_route():
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
                    task = {
                        "http_request": {  # Specify the type of request.
                            "http_method": tasks_v2.HttpMethod.POST,
                            "url": os.getenv('REFRESH_ULINC_COOKIE_TASK_HANDLER_URL'),
                            'body': json.dumps(payload).encode(),
                            'headers': {
                                'Content-type': 'application/json'
                            }
                        }
                    }
                    queue = 'refresh-ulinc-cookie'
                    if os.getenv('FLASK_ENV') == 'production':
                        parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue=queue)
                    else:
                        parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue=queue)
                    task_response = gc_tasks_client.create_task(parent=parent, task=task)
                    tasks.append({
                        "account_id": account.account_id,
                        "ulinc_config_id": ulinc_config.ulinc_config_id,
                        "task_id": task_response.name
                    })
    return jsonify(tasks)

@mod_jobs.route('/refresh_ulinc_campaigns', methods=['GET'])
@check_cron_header
def refresh_ulinc_campaigns_route():
    with get_db_session() as session:
        accounts = session.query(Account).filter(and_(
            and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
            and_(Account.payment_effective_start_date < datetime.utcnow(), Account.payment_effective_end_date > datetime.utcnow()),
            Account.account_id != Account.unassigned_account_id
        )).all()
        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id and ulinc_config.cookie_id != Cookie.unassigned_cookie_id:
                    payload = {
                        'ulinc_config_id': ulinc_config.ulinc_config_id,
                    }
                    task = {
                        "http_request": {  # Specify the type of request.
                            "http_method": tasks_v2.HttpMethod.POST,
                            "url": os.getenv('REFRESH_ULINC_CAMPAIGNS_TASK_HANDLER_URL'),
                            'body': json.dumps(payload).encode(),
                            'headers': {
                                'Content-type': 'application/json'
                            }
                        }
                    }
                    queue = 'refresh-ulinc-campaigns'
                    if os.getenv('FLASK_ENV') == 'production':
                        parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue=queue)
                    else:
                        parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue=queue)
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
                        # print(contact.contact_id)
                        payload = {
                            'contact_id': contact.contact_id,
                        }
                        task = {
                            "http_request": {  # Specify the type of request.
                                "http_method": tasks_v2.HttpMethod.POST,
                                "url": os.getenv('DATA_ENRICHMENT_TASK_HANDLER_URL'),
                                'body': json.dumps(payload).encode(),
                                'headers': {
                                    'Content-type': 'application/json'
                                }
                            }
                        }
                        queue = 'data-enrichment'
                        parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue=queue)
                        if os.getenv('FLASK_ENV') == 'production':
                            parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue=queue)

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

        send_email_parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send-email')
        send_li_message_parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send-li-message')
        if os.getenv('FLASK_ENV') == 'production':
            send_email_parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send-email')
            send_li_message_parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send-li-message')

        # send_li_message_parent = gc_tasks_client.queue_path('foundation-production', 'us-west3', queue='send-li-message')
        # send_email_parent = gc_tasks_client.queue_path('foundation-production', 'us-west3', queue='send-email')

        send_li_message_tasks = get_tasks(gc_tasks_client, send_li_message_parent)
        send_email_tasks = get_tasks(gc_tasks_client, send_email_parent)
        total_message_tasks = send_li_message_tasks + send_email_tasks
        email_timestamp_list = [task.schedule_time for task in send_email_tasks]

        total_message_contact_id_list = [json.loads(task.http_request.body)['contact_id'] for task in total_message_tasks]

        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                for janium_campaign in ulinc_config.janium_campaigns:
                    for target_dict in janium_campaign.get_email_targets():
                        if target_dict['contact_id'] not in total_message_contact_id_list: # If contact has existing outbound message task, skip
                            # Generate the timestamp to be used in task
                            # Ensure that tasks are at least 3 min apart
                            for i in range(1000):
                                scheduled_timestamp = janium_campaign.generate_random_timestamp_in_queue_interval()
                                for j in email_timestamp_list:
                                    timestamp_diff = abs(int((scheduled_timestamp - j).total_seconds()))
                                    if timestamp_diff < 2800:
                                        scheduled_timestamp = None
                                        break
                                    else:
                                        continue
                                if scheduled_timestamp:
                                    break

                            if scheduled_timestamp:
                                # Create Timestamp protobuf
                                timestamp = timestamp_pb2.Timestamp()
                                timestamp.FromDatetime(scheduled_timestamp)
                                payload = target_dict

                                send_email_task = {
                                    "http_request": {  # Specify the type of request.
                                        "http_method": tasks_v2.HttpMethod.POST,
                                        "url": os.getenv('SEND_EMAIL_TASK_HANDLER_URL'),
                                        'body': json.dumps(payload).encode(),
                                        'headers': {
                                            'Content-type': 'application/json'
                                        }
                                    }
                                }

                                # Add the timestamp to the tasks.
                                send_email_task['schedule_time'] = timestamp

                                task_response = gc_tasks_client.create_task(parent=send_email_parent, task=send_email_task)
                                tasks.append({
                                    "account_id": account.account_id,
                                    "ulinc_config_id": ulinc_config.ulinc_config_id,
                                    "janium_campaign_id": janium_campaign.janium_campaign_id,
                                    "email_target_details": target_dict,
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

        send_email_parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send-email')
        send_li_message_parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send-li-message')
        if os.getenv('FLASK_ENV') == 'production':
            send_email_parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send-email')
            send_li_message_parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send-li-message')

        # send_li_message_parent = gc_tasks_client.queue_path('foundation-production', 'us-west3', queue='send-li-message')
        # send_email_parent = gc_tasks_client.queue_path('foundation-production', 'us-west3', queue='send-email')

        send_li_message_tasks = get_tasks(gc_tasks_client, send_li_message_parent)
        send_email_tasks = get_tasks(gc_tasks_client, send_email_parent)
        total_message_tasks = send_li_message_tasks + send_email_tasks
        li_message_timestamp_list = [task.schedule_time for task in send_li_message_tasks]

        total_message_contact_id_list = [json.loads(task.http_request.body)['contact_id'] for task in total_message_tasks]

        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                if ulinc_config.ulinc_is_active and ulinc_config.is_working:
                    for janium_campaign in ulinc_config.janium_campaigns:
                        for target_dict in janium_campaign.get_li_message_targets():
                            if target_dict['contact_id'] not in total_message_contact_id_list: # If contact has existing outbound message task, skip
                                for i in range(1000):
                                    scheduled_timestamp = janium_campaign.generate_random_timestamp_in_queue_interval()
                                    for j in li_message_timestamp_list:
                                        timestamp_diff = abs(int((scheduled_timestamp - j).total_seconds()))
                                        if timestamp_diff < 2800:
                                            scheduled_timestamp = None
                                            break
                                        else:
                                            continue
                                    if scheduled_timestamp:
                                        break
                                # Generate the timestamp to be used in task
                                if scheduled_timestamp := janium_campaign.generate_random_timestamp_in_queue_interval():
                                    # Create Timestamp protobuf
                                    timestamp = timestamp_pb2.Timestamp()
                                    timestamp.FromDatetime(scheduled_timestamp)
                                    payload = target_dict
                                    send_li_message_task = {
                                        "http_request": {  # Specify the type of request.
                                            "http_method": tasks_v2.HttpMethod.POST,
                                            "url": os.getenv('SEND_LI_MESSAGE_TASK_HANDLER_URL'),
                                            'body': json.dumps(payload).encode(),
                                            'headers': {
                                                'Content-type': 'application/json'
                                            }
                                        }
                                    }
                                    # Add the timestamp to the tasks.
                                    send_li_message_task['schedule_time'] = timestamp

                                    task_response = gc_tasks_client.create_task(parent=send_li_message_parent, task=send_li_message_task)
                                    tasks.append({
                                        "account_id": account.account_id,
                                        "ulinc_config_id": ulinc_config.ulinc_config_id,
                                        "janium_campaign_id": janium_campaign.janium_campaign_id,
                                        "li_message_target_details": target_dict,
                                        "task_id": task_response.name,
                                        "scheduled_time": scheduled_timestamp
                                    })
                                    # break
    return jsonify(tasks)

@mod_jobs.route('/send_dte', methods=['GET'])
@check_cron_header
def send_dte_function():
    with get_db_session() as session:
        accounts = session.query(Account).filter(and_(
            and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
            and_(Account.payment_effective_start_date < datetime.utcnow(), Account.payment_effective_end_date > datetime.utcnow()),
            Account.is_receiving_dte == 1,
            Account.account_id != Account.unassigned_account_id
        )).all()

        send_dte_parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send-dte')
        if os.getenv('FLASK_ENV') == 'production':
            send_dte_parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send-dte')
        
        tasks = []
        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                payload = {
                    "ulinc_config_id": ulinc_config.ulinc_config_id,
                    "dte_id": account.dte_id,
                    "dte_sender_id": account.dte_sender_id
                }
                send_dte_task = {
                    "http_request": {  # Specify the type of request.
                        "http_method": tasks_v2.HttpMethod.POST,
                        "url": os.getenv('SEND_DTE_TASK_HANDLER_URL'),
                        'body': json.dumps(payload).encode(),
                        'headers': {
                            'Content-type': 'application/json'
                        }
                    }
                }

                task_response = gc_tasks_client.create_task(parent=send_dte_parent, task=send_dte_task)
                tasks.append({
                    "account_id": account.account_id,
                    "ulinc_config_id": ulinc_config.ulinc_config_id,
                    "task_id": task_response.name
                })
    return jsonify(tasks)

@mod_jobs.route('/send_dme', methods=['GET'])
@check_cron_header
def send_dme_function():
    send_dme_parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send-dme')
    if os.getenv('FLASK_ENV') == 'production':
        send_dme_parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), os.getenv('TASK_QUEUE_LOCATION'), queue='send-dme')
    
    send_dme_task = {
        "http_request": {  # Specify the type of request.
            "http_method": tasks_v2.HttpMethod.POST,
            "url": os.getenv('SEND_DME_TASK_HANDLER_URL'),
            'body': json.dumps({"body": "nothing"}).encode(),
            'headers': {
                'Content-type': 'application/json'
            }
        }
    }

    task_response = gc_tasks_client.create_task(parent=send_dme_parent, task=send_dme_task)

    return jsonify({'message': 'Sent to task handler'})