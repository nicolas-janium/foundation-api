from collections import namedtuple
import json
import os
from datetime import datetime, timedelta
from email.header import Header
from email.message import EmailMessage
from pprint import pprint
from unittest.mock import Mock

import boto3
import css_inline
from flask import Response, escape
import pandas as pd
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup as Soup

from model import (Account, Ulinc_config, Dte, Dte_sender, create_gcf_db_engine,
                   create_gcf_db_session)


def populate_table(ulinc_config, email_body, data_set_dict):
    soup = Soup(email_body, 'html.parser')
    type = str(data_set_dict['type'])
    tbody = soup.find("div", id=type.replace('_', '-')).tbody

    for i, item in enumerate(data_set_dict['data']):
        tr_tag = soup.new_tag("tr", **{'class': 'table-row'})
        redirect_url = "{}dte_click?click_type={}&redirect_url={}&contact_id={}".format(os.getenv('BACKEND_API_URL'), data_set_dict['type'], item['li_profile_url'], item['contact_id'])
        name_td = soup.new_tag("td", **{'class': 'tg-kmlv' if i % 2 == 0 else 'tg-vmfx'})
        name_a = soup.new_tag("a", href=redirect_url)
        name_a.string = str(item['full_name'])
        name_td.append(name_a)
        tr_tag.append(name_td)
        if data_set_dict['type'] in ['new_connection', 'new_message']:
            qual_td = soup.new_tag("td", **{'class': 'tg-kmlv' if i % 2 == 0 else 'tg-vmfx'})
            qual_url = "{}dte_click?click_type={}&contact_id={}&redirect_url={}".format(os.getenv('BACKEND_API_URL'), 'dq' if data_set_dict['type'] == 'new_connection' else 'continue', item['contact_id'], 'https://app.janium.io')
            qual_a = soup.new_tag(
                "a",
                href=qual_url,
                **{
                    'class': 'btn-{}'.format('remove' if data_set_dict['type'] == 'new_connection' else 'continue'),
                    'style': 'color:{}'.format('red' if data_set_dict['type'] == 'new_connection' else 'green')
                }
            )
            qual_a.string = 'DQ' if data_set_dict['type'] == 'new_connection' else 'Continue'
            qual_td.append(qual_a)
            tr_tag.append(qual_td)

        title_td = soup.new_tag("td", **{'class': 'tg-kmlv' if i % 2 == 0 else 'tg-vmfx'})
        title_td.string = item['title']
        tr_tag.append(title_td)

        company_td = soup.new_tag("td", **{'class': 'tg-kmlv' if i % 2 == 0 else 'tg-vmfx'})
        company_td.string = item['company']
        tr_tag.append(company_td)

        location_td = soup.new_tag("td", **{'class': 'tg-kmlv' if i % 2 == 0 else 'tg-vmfx'})
        location_td.string = item['location']
        tr_tag.append(location_td)

        ulinc_campaign_td = soup.new_tag("td", **{'class': 'tg-kmlv' if i % 2 == 0 else 'tg-vmfx', 'style': 'white-space: nowrap;overflow: hidden;text-overflow: ellipsis;'})
        ulinc_campaign_td.string = item['ulinc_campaign_name']
        tr_tag.append(ulinc_campaign_td)

        if data_set_dict['type'] == 'new_message':
            message_source_td = soup.new_tag("td", **{'class': 'tg-kmlv' if i % 2 == 0 else 'tg-vmfx'})
            message_source_td.string = 'Email' if item['message_source'] == 'email' else 'LinkedIn'
            tr_tag.append(message_source_td)

        if data_set_dict['type'] in ['new_connection', 'new_message']:
            action_timestamp_td = soup.new_tag("td", **{'class': 'tg-kmlv' if i % 2 == 0 else 'tg-vmfx'})
            action_timestamp_td.string = item['action_timestamp'].strftime(r'%m-%d-%Y')
            tr_tag.append(action_timestamp_td)

        if data_set_dict['type'] == 'voicemail':
            phone_td = soup.new_tag("td", **{'class': 'tg-kmlv' if i % 2 == 0 else 'tg-vmfx'})
            phone_td.string = item['phone']
            tr_tag.append(phone_td)

        tbody.append(tr_tag)
    return str(soup)

def tailor_email(email_body, ulinc_config):
    email_body = email_body.replace(r'{FirstName}', ulinc_config.ulinc_config_account.account_user.first_name)
    soup = Soup(email_body, 'html.parser')

    ulinc_inbox_tag = soup.find("a", id="ulinc-inbox")
    ulinc_inbox_tag['href'] = "https://ulinc.co/{}/all".format(ulinc_config.ulinc_client_id)

    return str(soup)

def send_email_with_ses(dte, email_body, dte_sender, recipient):
    main_email = EmailMessage()
    main_email.make_alternative()

    main_email['Subject'] = dte.dte_subject
    main_email['From'] = str(Header('{} <{}>')).format(dte_sender.dte_sender_full_name, dte_sender.dte_sender_from_email)

    # main_email['To'] = ['nic@janium.io', 'jason@janium.io']
    # main_email['To'] = ['nic@janium.io']
    main_email['MIME-Version'] = '1.0'


    main_email.add_alternative(email_body, 'html')

    client = boto3.client(
        'ses',
        region_name="us-east-2",
        aws_access_key_id=os.getenv('SES_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('SES_SECRET_ACCESS_KEY')
    )
    try:
        response = client.send_raw_email(
            Source=main_email['From'],
            # Destinations=[recipient],
            Destinations=['nic@janium.io'],
            RawMessage={
                "Data": main_email.as_string()
            }
        )

        return True
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
        return None

def main(request):
    json_body = request.get_json(force=True)
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        if ulinc_config := session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == json_body['ulinc_config_id']).first():
            if dte := session.query(Dte).filter(Dte.dte_id == json_body['dte_id']).first():
                if dte_sender := session.query(Dte_sender).filter(Dte_sender.dte_sender_id == json_body['dte_sender_id']).first():
                    data_sets = [
                        {
                            'type': 'new_connection',
                            'data': [
                                item for item in ulinc_config.get_dte_new_connections(session) if not (item['is_clicked'] or item['is_dqd'])
                            ]
                        },
                        {
                            'type': 'new_message',
                            'data': [
                                item for item in ulinc_config.get_dte_new_messages(session) if not (item['is_clicked'] or item['is_dqd'] or item['is_continue'])
                            ]
                        },
                        {
                            'type': 'voicemail',
                            'data': [
                                item for item in ulinc_config.get_dte_vm_tasks(session) if not (item['is_clicked'] or item['is_dqd'])
                            ]
                        }
                    ]
                    
                    email_body = dte.dte_body
                    for data_set in data_sets:
                        email_body = populate_table(ulinc_config, email_body, data_set)
                    
                    email_body = tailor_email(email_body, ulinc_config)

                    send_email_with_ses(dte, email_body, dte_sender, ulinc_config.ulinc_config_account.account_user.primary_email)
                    return Response("Success", 200)
                return Response("Unknown dte_sender_id", 200) # Task should not repeat
            return Response("Unknown dte_id", 200) # Task should not repeat
        return Response("Unknown ulinc_config_id", 200) # Task should not repeat

        


if __name__ == '__main__':
    data = {
        "ulinc_config_id": "d0b9f557-942c-4d5f-b986-8ff935ebce81",
        "dte_id": "e6c22b66-7679-46ab-a244-0c8828889885",
        "dte_sender_id": "ffbacac6-c188-4b7a-9411-4bdb00ecd660"
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    # pprint(func_res)
    print(func_res.status_code)



















# new_cnxn_cols = [
            #     'Name/LinkedIn', 'Qualification', 'Title', 'Company', 'Location', 'Janium Campaign', 'Ulinc Campaign', 'Connection Date'
            # ]

            # contacts = ulinc_config.get_dte_new_connections(session)

            # new_cnxn_df = pd.DataFrame(columns=new_cnxn_cols)
            # # new_cnxn_df.set_index('contact_id')
            # for contact in contacts:
            #     dte_click_url = "https://{}.wm.r.appspot.com/api/v1/dte_click?click_type=dq&contact_id={}".format(os.getenv('PROJECT_ID'), contact['contact_id'])
            #     contact_df = pd.DataFrame(
            #         [{
            #             'Name/LinkedIn': '<a href="{}">{}</a>'.format(contact['li_profile_url'], contact['full_name']),
            #             'Qualification': '<a href="{}">DQ</a>'.format(escape(dte_click_url)),
            #             'Title': contact['title'],
            #             'Company': contact['company'],
            #             'Location': contact['location'],
            #             'Janium Campaign': contact['janium_campaign_name'],
            #             'Ulinc Campaign': contact['ulinc_campaign_name'],
            #             'Connection Date': contact['connection_date'].strftime(r'%m-%d-%Y')
            #         }]
            #     )
            #     new_cnxn_df = pd.concat([new_cnxn_df, contact_df], ignore_index=True)
            # new_cnxn_html = new_cnxn_df.to_html(
            #     border=0,
            #     justify='left',
            #     classes='tg-cnxn',
            #     index=False,
            #     escape=False
            # )

            # dte = session.query(Dte).filter(Dte.dte_id == json_body['dte_id']).first()
            # print(dte.dte_body)

            # # print(new_cnxn_html)