import json
import os

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

def create_tasks_client():
    return tasks_v2.CloudTasksClient()

def create_tasks_parent(client, project_id, location, queue):
    return client.queue_path(project_id, location, queue=queue)

def create_app_engine_task(relative_uri, payload):
    return {
        'app_engine_http_request': {
            'http_method': tasks_v2.HttpMethod.POST,
            'relative_uri': relative_uri,
            'body': json.dumps(payload).encode(),
            'headers': {
                'Content-type': 'application/json'
            }
        }
    }

def create_url_task(url, payload):
    return {
        "http_request": {  # Specify the type of request.
            "http_method": tasks_v2.HttpMethod.POST,
            "url": "{}{}".format(os.getenv("BACKEND_API_URL"), url),
            'body': json.dumps(payload).encode(),
            'headers': {
                'Content-type': 'application/json'
            }
        }
    }

def send_task(client, parent, task):
    return client.create_task(parent=parent, task=task)
