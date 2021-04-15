"""add system, type and unassigned data records

Revision ID: 19ad6d22004d
Revises: 16b47d1171e8
Create Date: 2021-04-14 10:01:51.493024

"""

import json
import os
import uuid

import sqlalchemy as sa
from alembic import op
from foundation_api.sa_db import model
from sqlalchemy import (JSON, Boolean, Column, Computed, DateTime, ForeignKey,
                        Integer, PrimaryKeyConstraint, String, Table, Text,
                        create_engine, engine)
from sqlalchemy.sql import column, false, func, null, table, text, true

# revision identifiers, used by Alembic.
revision = '19ad6d22004d'
down_revision = '16b47d1171e8'
branch_labels = None
depends_on = None


user = table('user',
    column('user_id', String),
    column('first_name', String),
    column('last_name', String),
    column('primary_email', String),
    column('username', String),
    column('password', String),
    column('updated_by', String)
)
# user_permission_map = table('user_permission_map',
#     column('user_id', String),
#     column('permission_id', String),
#     column('updated_by', String)
# )
account_type = table('account_type',
    column('account_type_id', Integer),
    column('account_type_name', String),
    column('account_type_description', String)
)
# user_account_map = table('user_account_map',
#     column('user_id', String),
#     column('account_id', String),
#     column('updated_by', String)
# )
# user_proxy_map = table('user_proxy_map',
#     column('user_id', String),
#     column('account_id', String),
#     column('updated_by', String)
# )
contact_source_type = table('contact_source_type',
    column('contact_source_type_id', Integer),
    column('contact_source_type_name', String),
    column('contact_source_type_description', String)
)
janium_campaign_step_type = table('janium_campaign_step_type',
    column('janium_campaign_step_type_id', Integer),
    column('janium_campaign_step_type_name', String),
    column('janium_campaign_step_type_description', String)
)
action_type = table('action_type',
    column('action_type_id', Integer),
    column('action_type_name', String),
    column('action_type_description', String)
)
cookie_type = table('cookie_type',
    column('cookie_type_id', Integer),
    column('cookie_type_name', String),
    column('cookie_type_description', String)
)
email_server = table('email_server',
    column('email_server_id', String),
    column('email_server_name', String),
    column('smtp_address', String),
    column('smtp_ssl_port', Integer),
    column('smtp_tls_port', Integer),
    column('imap_address', String),
    column('imap_ssl_port', Integer)
)
credentials = table('credentials',
    column('credentials_id', String),
    column('username', String),
    column('password', String),
    column('updated_by', String)
)
cookie = table('cookie',
    column('cookie_id', String),
    column('cookie_type_id', Integer),
    column('cookie_json_value', String),
    column('updated_by', String)
)
ulinc_config = table('ulinc_config',
    column('ulinc_config_id', String),
    column('credentials_id', String),
    column('cookie_id', String),
    column('ulinc_client_id', String),
    column('new_connection_webhook', String),
    column('new_message_webhook', String),
    column('send_message_webhook', String),
    column('updated_by', String),
    column('account_id', String),
    column('ulinc_li_email', String),
    column('ulinc_is_active', Boolean)
)
email_config = table('email_config',
    column('email_config_id', String),
    column('credentials_id', String),
    column('email_server_id', String),
    column('is_sendgrid', Boolean),
    column('is_email_forward', Boolean),
    column('sendgrid_sender_id', String),
    column('updated_by', String),
    column('from_full_name', String),
    column('reply_to_address', String)
)
dte = table('dte',
    column('dte_id', String),
    column('dte_name', String),
    column('dte_description', String),
    column('dte_subject', String),
    column('dte_body', Text),
    column('updated_by', String)
)
dte_sender = table('dte_sender',
    column('dte_sender_id', String),
    column('user_id', String),
    column('email_config_id', String)
)
account_group = table('account_group',
    column('account_group_id', String),
    column('account_group_manager_id', String),
    column('dte_id', String),
    column('dte_sender_id', String),
    column('account_group_name', String),
    column('account_group_description', String),
    column('updated_by', String)
)
janium_campaign = table('janium_campaign',
    column('janium_campaign_id', String),
    column('account_id', String),
    column('ulinc_config_id', String),
    column('email_config_id', String),
    column('janium_campaign_name', String),
    column('janium_campaign_description', String),
    column('is_messenger', Boolean),
    column('queue_start_time', DateTime),
    column('queue_end_time', DateTime),
    column('updated_by', String),
    column('is_reply_in_email_thread', Boolean)
)
ulinc_campaign = table('ulinc_campaign',
    column('ulinc_campaign_id', String),
    column('account_id', String),
    column('ulinc_config_id', String),
    column('janium_campaign_id', String),
    column('ulinc_campaign_name', String),
    column('ulinc_ulinc_campaign_id', String),
    column('ulinc_is_active', Boolean),
    column('ulinc_is_messenger', Boolean),
    column('updated_by', String)
)
contact_source = table('contact_source',
    column('contact_source_id', String),
    column('account_id', String),
    column('contact_source_type_id', Integer),
    column('contact_source_json', JSON)
)
time_zone = table('time_zone',
    column('time_zone_id', String),
    column('time_zone_name', String),
    column('time_zone_code', String)
)
account = table('account',
    column('account_id', String),
    column('account_type_id', Integer),
    column('account_group_id', String),
    column('time_zone_id', String),
    column('is_sending_emails', Boolean),
    column('is_sending_li_messages', Boolean),
    column('is_receiving_dte', Boolean),
    column('updated_by', String)
)



def upgrade():
    system_user_id = model.User.system_user_id
    op.bulk_insert(user,
        [
            {
                'user_id': system_user_id,
                'first_name': 'Janium System',
                'last_name': 'Master User',
                'primary_email': 'jason@janium.io',
                'username': 'janium123',
                'password': 'janium123',
                'updated_by': system_user_id
            },
            {
                'user_id': model.User.unassigned_user_id,
                'first_name': 'Unassigned',
                'last_name': 'User',
                'primary_email': 'unassigned321@gmail.com',
                'username': 'unassigned123',
                'password': 'password123',
                'updated_by': system_user_id
            }
        ]
    )
    op.bulk_insert(account_type,
        [
            {'account_type_id': 1, 'account_type_name': 'janium_foundation', 'account_type_description': 'Janium Foundation'},
            {'account_type_id': 2, 'account_type_name': 'janium_action', 'account_type_description': 'Janium Action'},
            {'account_type_id': 3, 'account_type_name': 'janium_management', 'account_type_description': 'Janium Management'}
        ]
    )
    op.bulk_insert(contact_source_type,
        [
            {'contact_source_type_id': 1, 'contact_source_type_name': 'ulinc_webhook_nc', 'contact_source_type_description': 'Webhook Data from Ulinc New Connection Webhook'},
            {'contact_source_type_id': 2, 'contact_source_type_name': 'ulinc_webhook_nm', 'contact_source_type_description': 'Webhook Data from Ulinc New Message Webhook'},
            {'contact_source_type_id': 3, 'contact_source_type_name': 'ulinc_webhook_sm', 'contact_source_type_description': 'Webhook Data from Ulinc Send Message Webhook'},
            {'contact_source_type_id': 4, 'contact_source_type_name': 'ulinc_csv_export', 'contact_source_type_description': 'CSV export from Ulinc'}
        ]
    )
    op.bulk_insert(janium_campaign_step_type,
        [
            {'janium_campaign_step_type_id': 1, 'janium_campaign_step_type_name': 'li_message', 'janium_campaign_step_type_description': 'LinkedIn Message'},
            {'janium_campaign_step_type_id': 2, 'janium_campaign_step_type_name': 'email', 'janium_campaign_step_type_description': 'Email'},
            {'janium_campaign_step_type_id': 3, 'janium_campaign_step_type_name': 'text_message', 'janium_campaign_step_type_description': 'Text Message'},
            {'janium_campaign_step_type_id': 4, 'janium_campaign_step_type_name': 'pre_connection_email', 'janium_campaign_step_type_description': 'Pre connection email (Data enrichment)'}
        ]
    )
    op.bulk_insert(action_type,
        [
            {'action_type_id': 1, 'action_type_name': 'li_new_connection', 'action_type_description': 'The contact connection request accepted. Originates in Ulinc'},
            {'action_type_id': 2, 'action_type_name': 'li_new_message', 'action_type_description': 'The client received a new li message from this contact. Originates in Ulin'},
            {'action_type_id': 3, 'action_type_name': 'li_send_message', 'action_type_description': 'The client sent a li message to this contact. Originates in Janium through Ulinc'},
            {'action_type_id': 4, 'action_type_name': 'send_email', 'action_type_description': 'The client sent an email to this contact. Originates in Janium'},
            {'action_type_id': 5, 'action_type_name': 'contact_email_open', 'action_type_description': 'The contact opened a previously sent email'},
            {'action_type_id': 6, 'action_type_name': 'new_email', 'action_type_description': 'The contact sent an email to the client'},
            {'action_type_id': 7, 'action_type_name': 'email_blacklist', 'action_type_description': 'The contact unsubscribed from a sent email from the client'},
            {'action_type_id': 8, 'action_type_name': 'dte_profile_visit_nc', 'action_type_description': 'The client visited the LI profile of this contact. Originates in DTE New Connection section'},
            {'action_type_id': 9, 'action_type_name': 'dte_profile_visit_nm', 'action_type_description': 'The client visited the LI profile of this contact. Originates in DTE New Message section'},
            {'action_type_id': 10, 'action_type_name': 'dte_profile_visit_vm', 'action_type_description': 'The client visited the LI profile of this contact. Originates in DTE Voicemail section'},
            {'action_type_id': 11, 'action_type_name': 'marked_no_interest', 'action_type_description': 'The client disqualified this contact. Originates in DTE'},
            {'action_type_id': 12, 'action_type_name': 'arbitrary_response', 'action_type_description': 'The contact responded with an arbitrary response and further campaign steps should continue'},
            {'action_type_id': 13, 'action_type_name': 'ulinc_messenger_origin_message', 'action_type_description': 'This is the origin message for Ulinc Messenger Campaigns'},
            {'action_type_id': 14, 'action_type_name': 'continue_campaign', 'action_type_description': 'The contact connection request accepted if contact is backdated into a janium campaign'},
            {'action_type_id': 15, 'action_type_name': 'email_bounce', 'action_type_description': 'The contact was sent an email that bounced. Originates from Sendgrid'},
            {'action_type_id': 16, 'action_type_name': 'tib_new_vendor', 'action_type_description': 'When a new vendor registers on TIB'},
            {'action_type_id': 17, 'action_type_name': 'tib_new_vendor_retire', 'action_type_description': 'When a new vendor submits a meeting request'},
            {'action_type_id': 18, 'action_type_name': 'ulinc_in_queue', 'action_type_description': 'The contact is in ulincs queue. Pre connection request. Ulinc side'},
            {'action_type_id': 19, 'action_type_name': 'ulinc_connection_requested', 'action_type_description': 'The contact has been sent a connection request. Ulinc side'},
            {'action_type_id': 20, 'action_type_name': 'ulinc_connection_error', 'action_type_description': 'The contact''s connection request had an error. Ulinc side'},
            {'action_type_id': 21, 'action_type_name': 'ulinc_marked_to_later', 'action_type_description': 'Contact marked to later in Ulinc'},
            {'action_type_id': 22, 'action_type_name': 'kendo_data_enrichment', 'action_type_description': 'Data enrichment from Kendo Email'}
        ]
    )
    op.bulk_insert(cookie_type,
        [
            {'cookie_type_id': 1, 'cookie_type_name': 'Ulinc Cookie', 'cookie_type_description': 'Cookie for Ulinc accounts'}
        ]
    )
    op.bulk_insert(email_server,
        [
            {'email_server_id': model.Email_server.gmail_id, 'email_server_name': 'gmail', 'smtp_address': 'smtp.gmail.com', 'smtp_ssl_port': 465, 'smtp_tls_port': 587, 'imap_address': 'imap.gmail.com', 'imap_ssl_port': 993},
            {'email_server_id': str(uuid.uuid4()), 'email_server_name': 'office_365', 'smtp_address': 'smtp.office365.com', 'smtp_ssl_port': 465, 'smtp_tls_port': 587, 'imap_address': 'outlook.office365.com', 'imap_ssl_port': 993},
            {'email_server_id': str(uuid.uuid4()), 'email_server_name': 'yahoo_small_business', 'smtp_address': 'smtp.bizmail.yahoo.com', 'smtp_ssl_port': 465, 'smtp_tls_port': 587, 'imap_address': 'imap.mail.yahoo.com', 'imap_ssl_port': 993}
        ]
    )
    op.execute(
        credentials.insert().values(
            credentials_id=model.Credentials.unassigned_credentials_id,
            username='username',
            password='password',
            updated_by=model.User.system_user_id
        )
    )
    op.execute(
        cookie.insert().values(
            cookie_id=model.Cookie.unassigned_cookie_id,
            cookie_type_id=1,
            # cookie_json_value=json.dumps({'usr': '123', 'pwd': '123'})
            cookie_json_value = '{"usr": "123", "pwd": "123"}',
            updated_by=model.User.system_user_id
        )
    )
    op.execute(
        email_config.insert().values(
            email_config_id=model.Email_config.unassigned_email_config_id,
            credentials_id=model.Credentials.unassigned_credentials_id,
            email_server_id=model.Email_server.gmail_id,
            is_sendgrid=False,
            is_email_forward=False,
            sendgrid_sender_id=null(),
            updated_by=model.User.system_user_id,
            from_full_name='Unassigned Email Config',
            reply_to_address='unassigned321@gmail.com'
        )
    )
    op.execute(
        dte.insert().values(
            dte_id=model.Dte.unassigned_dte_id,
            dte_name='Unassigned Dte Name',
            dte_description='Unassigned Dte description',
            dte_subject='Unassigned Dte Subject',
            dte_body='Unassigned Dte Body',
            updated_by=model.User.system_user_id
        )
    )
    op.execute(
        dte_sender.insert().values(
            dte_sender_id=model.Dte_sender.unassigned_dte_sender_id,
            user_id=model.User.system_user_id,
            email_config_id=model.Email_config.unassigned_email_config_id
        )
    )
    op.execute(
        account_group.insert().values(
            account_group_id=model.Account_group.unassigned_account_group_id,
            account_group_manager_id=model.User.system_user_id,
            dte_id=model.Dte.unassigned_dte_id,
            dte_sender_id=model.Dte_sender.unassigned_dte_sender_id,
            account_group_name='Unassigned Account Group Name',
            account_group_description='Unassigned Account Group Description',
            updated_by=model.User.system_user_id
        )
    )
    mt_time_zone_id = str(uuid.uuid4())
    op.bulk_insert(time_zone,
        [
            {'time_zone_id': mt_time_zone_id, 'time_zone_name': 'Mountain Time', 'time_zone_code': 'US/Mountain'},
            {'time_zone_id': str(uuid.uuid4()), 'time_zone_name': 'Eastern Time', 'time_zone_code': 'US/Eastern'},
            {'time_zone_id': str(uuid.uuid4()), 'time_zone_name': 'Central Time', 'time_zone_code': 'US/Central'},
            {'time_zone_id': str(uuid.uuid4()), 'time_zone_name': 'Pacific Time', 'time_zone_code': 'US/Pacific'}
        ]
    )
    op.execute(
        account.insert().values(
            account_id=model.Account.unassigned_account_id,
            account_type_id=1,
            account_group_id=model.Account_group.unassigned_account_group_id,
            time_zone_id=mt_time_zone_id,
            is_sending_emails=False,
            is_sending_li_messages=False,
            is_receiving_dte=False,
            updated_by=model.User.system_user_id 
        )
    )
    op.execute(
        ulinc_config.insert().values(
            ulinc_config_id=model.Ulinc_config.unassigned_ulinc_config_id,
            credentials_id=model.Credentials.unassigned_credentials_id,
            cookie_id=model.Cookie.unassigned_cookie_id,
            ulinc_client_id='999',
            new_connection_webhook='123',
            new_message_webhook='123',
            send_message_webhook='123',
            updated_by=model.User.system_user_id,
            account_id=model.Account.unassigned_account_id,
            ulinc_li_email='unassigned@email.com',
            ulinc_is_active=False
        )
    )
    op.execute(
        janium_campaign.insert().values(
            janium_campaign_id=model.Janium_campaign.unassigned_janium_campaign_id,
            account_id=model.Account.unassigned_account_id,
            ulinc_config_id=model.Ulinc_config.unassigned_ulinc_config_id,
            email_config_id=model.Email_config.unassigned_email_config_id,
            janium_campaign_name='Unassigned Janium Campaign',
            janium_campaign_description='Unassigned Janium Campaign Description',
            is_messenger=False,
            queue_start_time=text("'9999-12-31 09:00:00'"),
            queue_end_time=text("'9999-12-31 12:00:00'"),
            updated_by=model.User.system_user_id,
            is_reply_in_email_thread=False
        )
    )
    op.execute(
        ulinc_campaign.insert().values(
            ulinc_campaign_id=model.Ulinc_campaign.unassigned_ulinc_campaign_id,
            janium_campaign_id=model.Janium_campaign.unassigned_janium_campaign_id,
            account_id=model.Account.unassigned_account_id,
            ulinc_config_id=model.Ulinc_config.unassigned_ulinc_config_id,
            ulinc_campaign_name='Unassigned Janium Campaign',
            ulinc_ulinc_campaign_id='999',
            ulinc_is_active=False,
            ulinc_is_messenger=False,
            updated_by=model.User.system_user_id
        )
    )


def downgrade():
    pass
