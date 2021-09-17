import json
import os

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

def create_tasks_client():
    return tasks_v2.CloudTasksClient()

def create_tasks_parent(client, project_id, location, queue):
    return client.queue_path(project_id, location, queue=queue)

def create_app_engine_task(relative_uri_path, payload):
    return {
        'app_engine_http_request': {
            'http_method': tasks_v2.HttpMethod.POST,
            'relative_uri': relative_uri_path,
            'body': json.dumps(payload).encode(),
            'headers': {
                'Content-type': 'application/json'
            }
        }
    }

def create_url_task(url, relative_uri_path, payload):
    return {
        "http_request": {  # Specify the type of request.
            "http_method": tasks_v2.HttpMethod.POST,
            "url": "{}{}".format(url, relative_uri_path),
            'body': json.dumps(payload).encode(),
            'headers': {
                'Content-type': 'application/json'
            }
        }
    }

def send_task(client, parent, task):
    return client.create_task(parent=parent, task=task)

def get_tasks(client, parent):
    list_tasks_request = tasks_v2.ListTasksRequest()
    list_tasks_request.parent = parent
    list_tasks_request.response_view = 2
    tasks = client.list_tasks(list_tasks_request)
    return [task for task in tasks]
    return [json.loads(task.http_request.body) for task in tasks]