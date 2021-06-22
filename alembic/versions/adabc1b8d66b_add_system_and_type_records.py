"""add system and type records

Revision ID: adabc1b8d66b
Revises: 7456095e65c9
Create Date: 2021-06-17 12:00:22.480443

"""
import json
import os
import uuid

import sqlalchemy as sa
from alembic import op
from foundation_api.V1.sa_db import model
from sqlalchemy import (JSON, Boolean, Column, Computed, DateTime, ForeignKey,
                        Integer, PrimaryKeyConstraint, String, Table, Text,
                        create_engine, engine)
from sqlalchemy.sql import column, false, func, null, table, text, true


# revision identifiers, used by Alembic.
revision = 'adabc1b8d66b'
down_revision = '7456095e65c9'
branch_labels = None
depends_on = None

credentials = table('credentials',
    column('credentials_id', String),
    column('username', String),
    column('password', String)
)

user = table('user',
    column('user_id', String),
    column('first_name', String),
    column('last_name', String),
    column('primary_email', String),
    column('credentials_id', String)
)
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
time_zone = table('time_zone',
    column('time_zone_id', String),
    column('time_zone_name', String),
    column('time_zone_code', String)
)
dte = table('dte',
    column('dte_id', String),
    column('dte_name', String),
    column('dte_description', String),
    column('dte_subject', String),
    column('dte_body', String)
)



def upgrade():
    janium_master_credentials_id = str(uuid.uuid4())
    op.execute(
        credentials.insert().values(
            credentials_id=janium_master_credentials_id,
            username='nic@janium.io',
            password='$2y$12$licUV4DEBt6eV5.8Zh1gROdBOKtHOZ87ihUHj5rFePTmVcOeaygCW '
        )
    )
    op.execute(
        credentials.insert().values(
            credentials_id=model.Credentials.unassigned_credentials_id,
            username='unassigned',
            password='123'
        )
    )

    janium_master_id = str(uuid.uuid4())
    op.bulk_insert(user,
        [
            {
                'user_id': janium_master_id,
                'first_name': 'Janium',
                'last_name': 'Master',
                'primary_email': 'nic@janium.io',
                'credentials_id': janium_master_credentials_id
            }
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
    op.bulk_insert(time_zone,
        [
            {'time_zone_id': str(uuid.uuid4()), 'time_zone_name': 'Mountain Time', 'time_zone_code': 'US/Mountain'},
            {'time_zone_id': str(uuid.uuid4()), 'time_zone_name': 'Eastern Time', 'time_zone_code': 'US/Eastern'},
            {'time_zone_id': str(uuid.uuid4()), 'time_zone_name': 'Central Time', 'time_zone_code': 'US/Central'},
            {'time_zone_id': str(uuid.uuid4()), 'time_zone_name': 'Pacific Time', 'time_zone_code': 'US/Pacific'}
        ]
    )
    op.bulk_insert(dte,
        [
            {'dte_id': model.Dte.unassigned_dte_id, 'dte_name': 'Unassigned DTE Name', 'dte_description': 'Unassigned DTE Description', 'dte_subject': 'DTE Subject', 'dte_body': 'DTE Body'}
        ]
    )


def downgrade():
    pass
