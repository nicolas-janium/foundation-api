from datetime import datetime, timedelta
from foundation_api.V1.utils import ulinc
import logging
from functools import wraps
import pytz
import json
import os
import random

from flask import Blueprint, jsonify, request, make_response
from sqlalchemy import and_
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from foundation_api.V1.sa_db.model import Contact_source, db
from foundation_api.V1.sa_db.model import Account, Ulinc_config, Action, Contact
from foundation_api.V1.utils.data_enrichment import data_enrichment_function
from foundation_api.V1.utils.send_email import send_email_function
from foundation_api.V1.utils.send_li_message import send_li_message_function


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

    tasks = []
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
                            "url": "https://0f4c82be59ff.ngrok.io/api/v1/tasks/poll_ulinc_webhook",
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
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        and_(Account.data_enrichment_start_date < datetime.utcnow(), Account.data_enrichment_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()

    tasks = []
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
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
                            "url": "https://0f4c82be59ff.ngrok.io/api/v1/tasks/poll_ulinc_csv",
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
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()
    tasks = []
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            for i, contact_source in enumerate(ulinc_config.contact_sources.filter(Contact_source.is_processed == 0).order_by(Contact_source.contact_source_type_id.asc()).all()):
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
                        "url": "https://30c4827ac01d.ngrok.io/api/v1/tasks/process_contact_source",
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
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()
    tasks = []
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id:
                # parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), 'us-central1', queue='process-cs-queue')
                parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='refresh-ulinc-data')
                payload = {
                    'ulinc_config_id': ulinc_config.ulinc_config_id,
                }
                task = {
                    "http_request": {  # Specify the type of request.
                        "http_method": tasks_v2.HttpMethod.POST,
                        "url": "https://0f4c82be59ff.ngrok.io/api/v1/tasks/refresh_ulinc_data",
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
                tasks.append({
                    "account_id": account.account_id,
                    "ulinc_config_id": ulinc_config.ulinc_config_id,
                    "task_id": task_response.name
                })
                # print(task_response.name)
    return jsonify(tasks)

@mod_jobs.route('/data_enrichment', methods=['GET'])
@check_cron_header
def data_enrichment_job():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        and_(Account.data_enrichment_start_date < datetime.utcnow(), Account.data_enrichment_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id
    )).all()

    tasks = []
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            for janium_campaign in ulinc_config.janium_campaigns:
                contacts  = janium_campaign.get_data_enrichment_targets()
                for contact in contacts:
                    # parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), 'us-central1', queue='process-cs-queue')
                    parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='data-enrichment')
                    payload = {
                        'contact_id': contact.contact_id,
                    }
                    task = {
                        "http_request": {  # Specify the type of request.
                            "http_method": tasks_v2.HttpMethod.POST,
                            "url": "https://1ba3b79c6304.ngrok.io/api/v1/tasks/data_enrichment",
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
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id,
        Account.is_sending_emails
    )).all()

    tasks = []
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            for janium_campaign in ulinc_config.janium_campaigns:
                now = datetime.utcnow()
                queue_start_time = janium_campaign.queue_start_time
                queue_end_time = janium_campaign.queue_end_time
                queue_start_time = datetime(now.year, now.month, now.day, queue_start_time.hour, queue_start_time.minute, 00)
                queue_end_time = datetime(now.year, now.month, now.day, queue_end_time.hour, queue_end_time.minute, 00)
                if now > queue_end_time:
                    print("Queue time period has passed")
                else:
                    if queue_start_time > now:
                        sec_to_add = random.randint(int((queue_start_time - now).total_seconds()), int((queue_end_time - now).total_seconds()))
                    else:
                        sec_to_add = random.randint(1, int((queue_end_time - now).total_seconds()))
                scheduled_time = now + timedelta(seconds=sec_to_add)
                # Create Timestamp protobuf.
                timestamp = timestamp_pb2.Timestamp()
                timestamp.FromDatetime(scheduled_time)
                

                targets = janium_campaign.get_email_targets()
                for target in targets:
                    # parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), 'us-central1', queue='process-cs-queue')
                    parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send-email')
                    payload = {
                        'email_target_details': target,
                    }
                    task = {
                        "http_request": {  # Specify the type of request.
                            "http_method": tasks_v2.HttpMethod.POST,
                            "url": "https://689d552b6129.ngrok.io/api/v1/tasks/send_email",
                            'body': json.dumps(payload).encode(),
                            'headers': {
                                'Content-type': 'application/json'
                            }
                        }
                    }
                    # Add the timestamp to the tasks.
                    task['schedule_time'] = timestamp

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
                    tasks.append({
                        "account_id": account.account_id,
                        "ulinc_config_id": ulinc_config.ulinc_config_id,
                        "janium_campaign_id": janium_campaign.janium_campaign_id,
                        "email_target_details": target,
                        "task_id": task_response.name
                    })
                    # break

    return jsonify(tasks)

@mod_jobs.route('/send_li_message', methods=['GET'])
@check_cron_header
def send_li_message_job():
    accounts = db.session.query(Account).filter(and_(
        and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
        Account.account_id != Account.unassigned_account_id,
        Account.is_sending_li_messages
    )).all()

    tasks = []
    for account in accounts:
        for ulinc_config in account.ulinc_configs:
            for janium_campaign in ulinc_config.janium_campaigns:

                now = datetime.utcnow()
                queue_start_time = janium_campaign.queue_start_time
                queue_end_time = janium_campaign.queue_end_time
                queue_start_time = datetime(now.year, now.month, now.day, queue_start_time.hour, queue_start_time.minute, 00)
                queue_end_time = datetime(now.year, now.month, now.day, queue_end_time.hour, queue_end_time.minute, 00)
                if now > queue_end_time:
                    print("Queue time period has passed")
                else:
                    if queue_start_time > now:
                        sec_to_add = random.randint(int((queue_start_time - now).total_seconds()), int((queue_end_time - now).total_seconds()))
                    else:
                        sec_to_add = random.randint(1, int((queue_end_time - now).total_seconds()))
                scheduled_time = now + timedelta(seconds=sec_to_add)
                # Create Timestamp protobuf.
                timestamp = timestamp_pb2.Timestamp()
                timestamp.FromDatetime(scheduled_time)                

                if targets := janium_campaign.get_li_message_targets():
                    for target in targets:
                        # parent = gc_tasks_client.queue_path(os.getenv('PROJECT_ID'), 'us-central1', queue='process-cs-queue')
                        parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send-li-message')
                        payload = {
                            'li_message_target_details': target,
                        }
                        task = {
                            "http_request": {  # Specify the type of request.
                                "http_method": tasks_v2.HttpMethod.POST,
                                "url": "https://19e107b98787.ngrok.io/api/v1/tasks/send_li_message",
                                'body': json.dumps(payload).encode(),
                                'headers': {
                                    'Content-type': 'application/json'
                                }
                            }
                        }
                        # Add the timestamp to the tasks.
                        task['schedule_time'] = timestamp

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
                        tasks.append({
                            "account_id": account.account_id,
                            "ulinc_config_id": ulinc_config.ulinc_config_id,
                            "janium_campaign_id": janium_campaign.janium_campaign_id,
                            "email_target_details": target,
                            "task_id": task_response.name,
                            "scheduled_time": scheduled_time,
                            "sent_li_message": 0
                        })
                        break

    return jsonify(tasks)

# @mod_jobs.route('/send_li_message', methods=['GET'])
# @check_cron_header
# def send_li_message():
#     accounts = db.session.query(Account).filter(and_(
#         and_(Account.effective_start_date < datetime.utcnow(), Account.effective_end_date > datetime.utcnow()),
#         Account.account_id != Account.unassigned_account_id,
#         Account.is_sending_li_messages
#     )).all()

#     fail_list = []
#     success_list = []
#     for account in accounts:
#         account_local_time = datetime.now(pytz.timezone('UTC')).astimezone(pytz.timezone(account.time_zone.time_zone_code)).replace(tzinfo=None)
#         for ulinc_config in account.ulinc_configs:
#             for janium_campaign in ulinc_config.janium_campaigns:
#                 effective_dates_dict = janium_campaign.get_effective_dates(account.time_zone.time_zone_code)
#                 queue_times_dict = janium_campaign.get_queue_times(account.time_zone.time_zone_code)
#                 if (effective_dates_dict['start'] <= account_local_time <= effective_dates_dict['end']) and (queue_times_dict['start'].hour <= account_local_time.hour <= queue_times_dict['end'].hour):
#                     try:
#                         task_res = send_li_message_function(account, ulinc_config, janium_campaign, account_local_time, queue_times_dict)
#                         success_list.append({"account_id": account.account_id, "janium_campaign_id": janium_campaign.janium_campaign_id, "li_message_recipients": task_res})
#                     except Exception as err:
#                         logger.error("Send LI message error for account {}: {}".format(account.account_id, err))
#                         fail_list.append({"account_id": account.account_id})
#     return jsonify({"send_li_message_fail_list": fail_list, "send_li_message_success_list": success_list})
