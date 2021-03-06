import json
import os
from datetime import datetime, timedelta
from email.header import Header
from email.message import EmailMessage
from pprint import pprint
from unittest.mock import Mock

import boto3
import css_inline
from flask import Response
import pandas as pd
import requests
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup as Soup
from sqlalchemy.sql import text
from urllib3.exceptions import InsecureRequestWarning

from model import (Account, Ulinc_config, Dte, Dte_sender, create_gcf_db_engine,
                   create_gcf_db_session)

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning) # pylint: disable=no-member


def get_ulinc_tasks_count(ulinc_config):
    url = 'https://ulinc.co/{}/tasks/?do=tasks&act=upcoming'.format(ulinc_config.ulinc_client_id)

    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', ulinc_config.cookie.cookie_json_value['usr'])
    jar.set('pwd', ulinc_config.cookie.cookie_json_value['pwd'])

    headers = {
        "Accept": "application/json"
    }

    res = requests.get(url=url, cookies=jar, headers=headers)
    # print(res.text)
    if res.ok:
        if len(res.text) > 100:
            soup = Soup(res.text, 'html.parser')
            showing = soup.find('div', **{'class': 'showing'})
            strongs = showing.find_all('strong')
            return strongs[2].text
        else:
            return 0
    else:
        return 0

def get_ulinc_data(ulinc_config, session):
    url = 'https://ulinc.co/{}/'.format(ulinc_config.ulinc_client_id)

    jar = requests.cookies.RequestsCookieJar()
    jar.set('usr', ulinc_config.cookie.cookie_json_value['usr'])
    jar.set('pwd', ulinc_config.cookie.cookie_json_value['pwd'])

    res = requests.get(url=url, cookies=jar)
    if res.ok:
        soup = Soup(res.text, 'html.parser')
        stat_table = soup.find_all('table')[1]
        stat_df = pd.read_html(str(stat_table), flavor='bs4')[0]

        query = text("""
            select IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 25 and act.action_type_id = 3 then 1 else 0 end), 0) as LS1D,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 169 and act.action_type_id = 3 then 1 else 0 end), 0) as LS1W,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 721 and act.action_type_id = 3 then 1 else 0 end), 0) as LS1M,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 25 and act.action_type_id = 2 then 1 else 0 end), 0) as LR1D,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 169 and act.action_type_id = 2 then 1 else 0 end), 0) as LR1W,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 721 and act.action_type_id = 2 then 1 else 0 end), 0) as LR1M,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 25 and act.action_type_id = 4 and jcs.janium_campaign_step_type_id = 2 then 1 else 0 end), 0) as ES1D,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 169 and act.action_type_id = 4 and jcs.janium_campaign_step_type_id = 2 then 1 else 0 end), 0) as ES1W,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 721 and act.action_type_id = 4 and jcs.janium_campaign_step_type_id = 2 then 1 else 0 end), 0) as ES1M,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 25 and act.action_type_id = 4 and jcs.janium_campaign_step_type_id = 4 then 1 else 0 end), 0) as PES1D,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 169 and act.action_type_id = 4 and jcs.janium_campaign_step_type_id = 4 then 1 else 0 end), 0) as PES1W,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 721 and act.action_type_id = 4 and jcs.janium_campaign_step_type_id = 4 then 1 else 0 end), 0) as PES1M,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 25 and act.action_type_id = 6 then 1 else 0 end), 0) as ER1D,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 169 and act.action_type_id = 6 then 1 else 0 end), 0) as ER1W,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 721 and act.action_type_id = 6 then 1 else 0 end), 0) as ER1M,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 25 and act.action_type_id = 22 then 1 else 0 end), 0) as DE1D,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 169 and act.action_type_id = 22 then 1 else 0 end), 0) as DE1W,
                IFNULL(sum(case when timestampdiff(HOUR, act.action_timestamp, NOW()) < 721 and act.action_type_id = 22 then 1 else 0 end), 0) as DE1M
            from action act
            inner join janium_campaign_step jcs on act.janium_campaign_step_id = jcs.janium_campaign_step_id
            inner join contact co on co.contact_id = act.contact_id
            inner join ulinc_campaign uca on co.ulinc_campaign_id = uca.ulinc_campaign_id
            inner join ulinc_config uc on uc.ulinc_config_id = uc.ulinc_config_id
            where uc.ulinc_config_id = '{}';
            """.format(ulinc_config.ulinc_config_id))

        ls_stats = session.execute(query)
        for row in ls_stats:
            ls1d = int(row[0])
            ls1w = int(row[1])
            ls1m = int(row[2])
            lr1d = int(row[3])
            lr1w = int(row[4])
            lr1m = int(row[5])
            es1d = int(row[6])
            es1w = int(row[7])
            es1m = int(row[8])
            pes1d = int(row[9])
            pes1w = int(row[10])
            pes1m = int(row[11])
            er1d = int(row[12])
            er1w = int(row[13])
            er1m = int(row[14])
            de1d = int(row[15])
            de1w = int(row[16])
            de1m = int(row[17])


        df = pd.DataFrame(
            {
                "User": ulinc_config.ulinc_config_account.account_user.full_name,
                "Ulinc LI Email": ulinc_config.ulinc_li_email,
                "IPA": ulinc_config.ulinc_config_account.is_payment_active(),
                "DTE Name": ulinc_config.ulinc_config_account.dte.dte_name if ulinc_config.ulinc_config_account.is_receiving_dte else None,
                "DTE Sender": ulinc_config.ulinc_config_account.dte_sender.dte_sender_full_name if ulinc_config.ulinc_config_account.is_receiving_dte else None,
                "UIQ": [int(get_ulinc_tasks_count(ulinc_config))],
                "CRD": [stat_df.at[1,1]],
                "CRW": [stat_df.at[1,4]],
                "CRM": [stat_df.at[1,5]],
                "CD": [stat_df.at[2,1]],
                "CW": [stat_df.at[2,4]],
                "CM": [stat_df.at[2,5]],
                "LSD": [ls1d],
                "LSW": [ls1w],
                "LSM": [ls1m],
                "LRD": [lr1d],
                "LRW": [lr1w],
                "LRM": [lr1m],
                "ESD": [es1d],
                "ESW": [es1w],
                "ESM": [es1m],
                "PESD": [pes1d],
                "PESW": [pes1w],
                "PESM": [pes1m],
                "ERD": [er1d],
                "ERW": [er1w],
                "ERM": [er1m],
                "DED": [de1d],
                "DEW": [de1w],
                "DEM": [de1m]
            }
        )
        return df

def send_email_with_ses(df_html):
    main_email = EmailMessage()
    main_email.make_alternative()

    main_email['Subject'] = 'Janium Production DME'
    main_email['From'] = str(Header('{} <{}>')).format('Janium Support', 'support@janium.io')

    # main_email['To'] = ['nic@janium.io', 'jason@janium.io']
    # main_email['To'] = ['nic@janium.io']
    main_email['MIME-Version'] = '1.0'


    main_email.add_alternative(df_html, 'html')

    client = boto3.client(
        'ses',
        region_name="us-east-2",
        aws_access_key_id=os.getenv('SES_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('SES_SECRET_ACCESS_KEY')
    )
    try:
        response = client.send_raw_email(
            Source=main_email['From'],
            Destinations=['nic@janium.io', 'jason@janium.io'],
            # Destinations=['nic@janium.io'],
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
        accounts = session.query(Account).filter(Account.account_id != Account.unassigned_account_id).all()

        columns = [
            'User', 'Ulinc LI Email', 'IPA', 'DTE Name', 'DTE Sender', 'UIQ',
            'CRD', 'CRW', 'CRM',
            'CD', 'CW', 'CM',
            'LSD', 'LSW', 'LSM',
            'LRD', 'LRW', 'LRM',
            'ESD', 'ESW', 'ESM',
            'PESD', 'PESW', 'PESM',
            'ERD', 'ERW', 'ERM',
            'DED', 'DEW', 'DEM'
        ]

        main_df = pd.DataFrame(columns=columns)

        for account in accounts:
            for ulinc_config in account.ulinc_configs:
                if ulinc_config.ulinc_config_id != Ulinc_config.unassigned_ulinc_config_id:
                    df = get_ulinc_data(ulinc_config, session)
                    if not df.empty:
                        main_df = pd.concat([main_df, df], ignore_index=True)
        
        css_style = u"""
            <head>
                <style type="text/css">
                    .stat_table{
                        width:100%;
                        padding: 0;
                        margin: 0;
                        border: 0;
                        border-collapse: collapse;
                        text-align: left;
                    }
                    .stat_table td{
                        padding: 5px;
                        text-align: left;
                    }
                    .stat_table th{
                        border-bottom: black 1px solid;
                        padding: 5px;
                    }

                    .stat_table tr td:nth-child(n+1):nth-last-child(n+24) {
                        background: #FFC09F;
                    }

                    .stat_table tr td:nth-child(n+4):nth-last-child(n+21) {
                        background: #B6DBE2;
                    }

                    .stat_table tr td:nth-child(n+7):nth-last-child(n+18) {
                        background: #99CDD5;
                    }

                    .stat_table tr td:nth-child(n+10):nth-last-child(n+15) {
                        background: #B6DBE2;
                    }

                    .stat_table tr td:nth-child(n+13):nth-last-child(n+12) {
                        background: #99CDD5;
                    }

                    .stat_table tr td:nth-child(n+16):nth-last-child(n+9) {
                        background: #B6DBE2;
                    }

                    .stat_table tr td:nth-child(n+19):nth-last-child(n+6) {
                        background: #99CDD5;
                    }

                    .stat_table tr td:nth-child(n+22):nth-last-child(n+4) {
                        background: #B6DBE2;
                    }

                    .stat_table tr td:nth-child(n+25):nth-last-child(n+1) {
                        background: #99CDD5;
                    }

                    .stat_table th:nth-child(n+1):nth-last-child(n+24) {
                        background: #FFC09F;
                    }

                    .stat_table th:nth-child(n+4):nth-last-child(n+21) {
                        background: #B6DBE2;
                    }

                    .stat_table th:nth-child(n+7):nth-last-child(n+18) {
                        background: #99CDD5;
                    }

                    .stat_table th:nth-child(n+10):nth-last-child(n+15) {
                        background: #B6DBE2;
                    }

                    .stat_table th:nth-child(n+13):nth-last-child(n+12) {
                        background: #99CDD5;
                    }

                    .stat_table th:nth-child(n+16):nth-last-child(n+9) {
                        background: #B6DBE2;
                    }

                    .stat_table th:nth-child(n+19):nth-last-child(n+6) {
                        background: #99CDD5;
                    }

                    .stat_table th:nth-child(n+22):nth-last-child(n+4) {
                        background: #B6DBE2;
                    }

                    .stat_table th:nth-child(n+25):nth-last-child(n+1) {
                        background: #99CDD5;
                    }
                </style>
            </head>
        """

        main_html = "<html>{}{}</html>".format(css_style, main_df.to_html(border=0, justify='left', classes='stat_table', index=False))
        main_html = css_inline.inline(main_html)

        send_email_with_ses(df_html=main_html)
    return Response("Success", 200) # Should not repeat

        


if __name__ == '__main__':
    data = {}
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    # pprint(func_res)
    print(func_res.status_code)
