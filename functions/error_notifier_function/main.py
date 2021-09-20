import base64
import json
import os
from email.header import Header
from email.message import EmailMessage

import boto3
from botocore.exceptions import ClientError
import requests


def send_email_with_ses(text_payload, resource_name='gae_app'):
    main_email = EmailMessage()
    main_email.make_alternative()

    main_email['Subject'] = "Janium {} Error in {}".format(os.getenv('PROJECT_ID'), resource_name)
    main_email['From'] = str(Header('{} <{}>')).format('Janium Support', 'support@janium.io')

    main_email['To'] = 'nic@janium.io'
    main_email['MIME-Version'] = '1.0'

    # main_email.add_alternative(html2text(email_html), 'plain')
    main_email.add_alternative(text_payload, 'plain')

    client = boto3.client(
        'ses',
        region_name="us-east-2",
        aws_access_key_id=os.getenv('SES_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('SES_SECRET_ACCESS_KEY')
    )
    try:
        response = client.send_raw_email(
            Source=main_email['From'],
            Destinations=[main_email['To']],
            RawMessage={
                "Data": main_email.as_string()
            }
        )
        return True
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
        return None

def main(event, context):
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    payload_json = json.loads(pubsub_message)

    if payload_json['resource']['type'] == 'cloud_function':
        return send_email_with_ses(payload_json['textPayload'], resource_name=payload_json['resource']['labels']['function_name'])
    
    return send_email_with_ses(payload_json['textPayload'])
