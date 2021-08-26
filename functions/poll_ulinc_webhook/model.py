import random
from contextlib import contextmanager
from datetime import datetime, timedelta
import os

import pytz
import requests
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (JSON, Boolean, Column, Computed, DateTime, ForeignKey,
                        Integer, String, Text, and_, create_engine, engine)
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.sql import false, text, true
from sqlalchemy.sql.expression import cast
from sqlalchemy.ext.declarative import declarative_base
from workdays import networkdays

db = SQLAlchemy(session_options={"autocommit": False, "autoflush": False}, engine_options={'pool_size': 10, 'max_overflow': 2})
Base = declarative_base()

@contextmanager
def get_db_session():
    try:
        yield db.session
    finally:
        db.session.remove()

def create_gcf_db_engine():
    db_url = engine.url.URL(
        drivername='mysql+pymysql',
        username= os.getenv('DB_USER'),
        password= os.getenv('DB_PASSWORD'),
        database= os.getenv('DB_NAME'),
        host= os.getenv('DB_HOST'),
        port= os.getenv('DB_PORT', 3306)
    )
    return create_engine(db_url)

def create_gcf_db_session(db_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    return Session


class User(Base):
    __tablename__ = 'user'
    unassigned_user_id = '9d34bb21-7037-4709-bb0f-e1e8b1491506'
    system_user_id = 'a0bcc7a2-5e2b-41c6-9d5c-ba8ebb01c03d'

    def __init__(self, user_id, credentials_id, first_name, last_name, title, company, location, primary_email, additional_contact_info, phone):
        self.user_id = user_id
        self.credentials_id = credentials_id
        self.first_name = first_name
        self.last_name = last_name
        self.title = title
        self.company = company
        self.location = location
        self.primary_email = primary_email
        self.parse_email = "{}.{}@parse.janium.io".format(first_name, last_name)
        self.additional_contact_info = additional_contact_info
        self.phone = phone
    
    user_id = Column(String(36), primary_key=True, nullable=False)

    credentials_id = Column(String(36), ForeignKey('credentials.credentials_id'), nullable=False)

    first_name = Column(String(126), nullable=False)
    last_name = Column(String(126), nullable=False)
    full_name = Column(String(256), Computed("CONCAT(first_name, ' ', last_name)"))
    title = Column(String(256), nullable=True)
    company = Column(String(256), nullable=True)
    location = Column(String(256), nullable=True)
    primary_email = Column(String(256), nullable=False)
    parse_email = Column(String(256), nullable=False)
    phone = Column(String(256), nullable=True)
    additional_contact_info = Column(JSON, nullable=True)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))

    account = relationship('Account', uselist=False, lazy=True)
    credentials = relationship('Credentials', backref=backref('credentials_user', uselist=False), uselist=False)

class Account(Base):
    __tablename__ = 'account'
    unassigned_account_id = '8acafb6b-3ce5-45b5-af81-d357509ba457'

    def __init__(self, account_id, user_id, is_sending_emails, is_sending_li_messages,
                       is_receiving_dte, effective_start_date, effective_end_date, data_enrichment_start_date,
                       data_enrichment_end_date, time_zone_id, dte_id='e18bd1b0-b404-41ac-a5e4-bcb112ced90d', dte_sender_id='70f29ac6-edc0-452b-8d7b-3d3ee87c09f0'):
        self.account_id = account_id
        self.user_id = user_id
        self.is_sending_emails = is_sending_emails
        self.is_sending_li_messages = is_sending_li_messages
        self.is_receiving_dte = is_receiving_dte
        self.effective_start_date = effective_start_date
        self.effective_end_date = effective_end_date
        self.data_enrichment_start_date = data_enrichment_start_date
        self.data_enrichment_end_date = data_enrichment_end_date
        self.time_zone_id = time_zone_id
        self.dte_id = dte_id
        self.dte_sender_id = dte_sender_id

    account_id = Column(String(36), primary_key=True)

    user_id = Column(String(36), ForeignKey('user.user_id'), nullable=False)
    time_zone_id = Column(String(36), ForeignKey('time_zone.time_zone_id'), nullable=False)
    dte_id = Column(String(36), ForeignKey('dte.dte_id'), nullable=False)
    dte_sender_id = Column(String(36), ForeignKey('dte_sender.dte_sender_id'), nullable=False)

    is_sending_emails = Column(Boolean, server_default=false(), nullable=False)
    is_sending_li_messages = Column(Boolean, server_default=false(), nullable=False)
    is_receiving_dte = Column(Boolean, server_default=false(), nullable=False)
    is_polling_ulinc = Column(Boolean, server_default=false(), nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    payment_effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    payment_effective_end_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    data_enrichment_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    data_enrichment_end_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences
    email_configs = relationship('Email_config', backref=backref('email_config_account', uselist=False), uselist=True, lazy=True)
    ulinc_configs = relationship('Ulinc_config', backref=backref('ulinc_config_account', uselist=False), uselist=True, lazy=True)
    time_zone = relationship('Time_zone', backref=backref('tz_account', uselist=True), uselist=False, lazy=True)
    dte = relationship('Dte', uselist=False, lazy=True)
    dte_sender = relationship('Dte_sender', uselist=False, lazy=True)

    def is_active(self):
        if self.effective_start_date < datetime.utcnow() <= self.effective_end_date:
            return True
        return False
    
    def is_payment_active(self):
        if self.payment_effective_start_date < datetime.utcnow() <= self.payment_effective_end_date:
            return True
        return False
    
    def convert_utc_to_account_local(self, dt_object):
        return pytz.utc.localize(dt_object).astimezone(pytz.timezone(self.time_zone.time_zone_code)).replace(tzinfo=None)
    
    def convert_account_local_to_utc(self, dt_object):
        local_tz = pytz.timezone(self.time_zone.time_zone_code)
        local_time = local_tz.localize(dt_object)
        utc_time = local_time.astimezone(pytz.utc)
        return utc_time

    def create_campaign_queue_time(self, hour, minute):
        local_tz = pytz.timezone(self.time_zone.time_zone_code)
        queue_time =  datetime(9999, 1, 1, hour, minute, 00) # Doesn't really matter
        queue_time = local_tz.localize(queue_time)
        queue_time = queue_time.astimezone(pytz.utc)
        return queue_time


class Ulinc_config(Base):
    __tablename__ = 'ulinc_config'
    unassigned_ulinc_config_id = 'dff0e400-b338-4bc5-bb99-617bade305bd'

    def __init__(self, ulinc_config_id, account_id, credentials_id, cookie_id, ulinc_client_id, new_connection_webhook, new_message_webhook, send_message_webhook, ulinc_li_email, ulinc_is_active):
        self.ulinc_config_id = ulinc_config_id
        self.account_id = account_id
        self.credentials_id = credentials_id
        self.cookie_id = cookie_id
        self.ulinc_client_id = ulinc_client_id
        self.new_connection_webhook = new_connection_webhook
        self.new_message_webhook = new_message_webhook
        self.send_message_webhook = send_message_webhook
        self.ulinc_li_email = ulinc_li_email
        self.ulinc_is_active = ulinc_is_active

    # Primary Keys
    ulinc_config_id = Column(String(36), primary_key=True)

    # Foreign Keys
    credentials_id = Column(String(36), ForeignKey('credentials.credentials_id'), nullable=False)
    cookie_id = Column(String(36), ForeignKey('cookie.cookie_id'), nullable=False)
    account_id = Column(String(36), ForeignKey('account.account_id'), nullable=False)

    # Common Columns
    ulinc_client_id = Column(String(16), nullable=False)
    ulinc_li_email = Column(String(64), nullable=False)
    ulinc_is_active = Column(Boolean, nullable=False)
    new_connection_webhook = Column(String(256), nullable=False)
    new_message_webhook = Column(String(256), nullable=False)
    send_message_webhook = Column(String(256), nullable=False)
    is_working = Column(Boolean, server_default=true(), nullable=False)

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    # updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    credentials = relationship('Credentials', uselist=False)
    cookie = relationship('Cookie', uselist=False)
    janium_campaigns = relationship('Janium_campaign', backref=backref('janium_campaign_ulinc_config', uselist=False), uselist=True)
    ulinc_campaigns = relationship('Ulinc_campaign', backref=backref('ulinc_config', uselist=False), uselist=True)
    contact_sources = relationship('Contact_source', uselist=True, lazy='dynamic')

    def create_cookie_jar(self):
        if cookie := self.cookie:
            jar = requests.cookies.RequestsCookieJar()
            jar.set('usr', cookie.cookie_json_value['usr'])
            jar.set('pwd', cookie.cookie_json_value['pwd'])
            return jar
        return None

    def get_webhooks(self):
        return [
            {"url": self.new_connection_webhook, "type": 1},
            {"url": self.new_message_webhook, "type": 2},
            {"url": self.send_message_webhook, "type": 3}
        ]

    def get_janium_campaigns(self):
        janium_campaigns = []
        for jc in self.janium_campaigns:
            janium_campaigns.append(
                {
                    "janium_campaign_id": jc.janium_campaign_id,
                    "janium_campaign_name": jc.janium_campaign_name,
                    "janium_campaign_description": jc.janium_campaign_description,
                    "janium_campaign_type": "Messenger" if jc.is_messenger else "Connector",
                    "janium_campaign_is_active": jc.is_active(),
                    "janium_campaign_contacts": jc.get_total_num_contacts(),
                    "janium_campaign_connected": jc.get_total_num_connections(),
                    "janium_campaign_replied": jc.get_total_num_responses()
                }
            )
        return janium_campaigns

    def get_ulinc_campaigns(self):
        ulinc_campaigns = []
        for uc in self.ulinc_campaigns:
            ulinc_campaigns.append(
                {
                    "ulinc_campaign_id": uc.ulinc_campaign_id,
                    "ulinc_campaign_name": uc.ulinc_campaign_name,
                    "ulinc_ulinc_campaign_id": uc.ulinc_ulinc_campaign_id,
                    "ulinc_is_active": uc.ulinc_is_active,
                    "parent_janium_camapaign_id": None if uc.parent_janium_campaign.janium_campaign_id == "65c96bb2-0c32-4858-a913-ca0cd902f1fe" else uc.parent_janium_campaign.janium_campaign_id,
                    "parent_janium_camapaign_name": None if uc.parent_janium_campaign.janium_campaign_id == "65c96bb2-0c32-4858-a913-ca0cd902f1fe" else uc.parent_janium_campaign.janium_campaign_name
                }
            )
        return sorted(ulinc_campaigns, key = lambda item: item['ulinc_campaign_name'])

    def get_summary_data(self):
        summary_data = {
            "new_connections": {"24h": 0, "72h": 0, "week": 0, "month": 0, "total": 0},
            "li_responses": {"24h": 0, "72h": 0, "week": 0, "month": 0, "total": 0},
            "li_messages_sent": {"24h": 0, "72h": 0, "week": 0, "month": 0, "total": 0},
            "email_responses": {"24h": 0, "72h": 0, "week": 0, "month": 0, "total": 0},
            "email_messages_sent": {"24h": 0, "72h": 0, "week": 0, "month": 0, "total": 0}
        }

        for ulinc_campaign in self.ulinc_campaigns:
            ulinc_campaign_summary_data = ulinc_campaign.get_summary_data()
            for key, value in ulinc_campaign_summary_data.items():
                summary_data[key]['24h'] += value['24h']
                summary_data[key]['72h'] += value['72h']
                summary_data[key]['week'] += value['week']
                summary_data[key]['month'] += value['month']
                summary_data[key]['total'] += value['total']

        return summary_data
    
    def get_dte_new_connections(self):
        new_connections_list = []
        for ulinc_campaign in self.ulinc_campaigns:
            new_connections_list += ulinc_campaign.get_dte_new_connections()
        return new_connections_list[0:100]
    
    def get_dte_new_messages(self):
        new_messages_list = []
        for ulinc_campaign in self.ulinc_campaigns:
            new_messages_list += ulinc_campaign.get_dte_new_messages()
        return new_messages_list[0:100]
    
    def get_dte_vm_tasks(self):
        vm_tasks_list = []
        for ulinc_campaign in self.ulinc_campaigns:
            vm_tasks_list += ulinc_campaign.get_dte_vm_tasks()
        return vm_tasks_list[0:100]

class Email_config(Base):
    __tablename__ = 'email_config'
    janium_email_config_id = '709f79b3-7a20-43ff-844a-4f014fa4e406'
    unassigned_email_config_id = '7c5c4aa2-2c6e-4e3d-947e-6efdae4366a1'

    def __init__(
        self,
        email_config_id, account_id, from_full_name, from_address,
        credentials_id='264f534f-d36e-4c3c-9614-9760f47ee0e3',
        email_server_id='936dce84-b50f-4b72-824f-b01989b20500',
        is_sendgrid=False, is_sendgrid_domain_verified=False, is_smtp=False, is_ses=False,
        is_ses_identity_requested=False, is_ses_identity_verified=False, is_ses_dkim_requested=False, is_ses_dkim_verified=False,
        is_ses_domain_requested=False, is_ses_domain_verified=False,
        is_email_forward=False, is_email_forward_verified=False, is_reply_proxy=False):
        self.email_config_id = email_config_id
        self.account_id = account_id
        self.credentials_id = credentials_id
        self.email_server_id = email_server_id
        self.is_email_forward = is_email_forward
        self.is_email_forward_verified = is_email_forward_verified
        self.from_full_name = from_full_name
        self.from_address = from_address
        self.is_sendgrid = is_sendgrid
        self.is_sendgrid_domain_verified = is_sendgrid_domain_verified 
        self.is_smtp = is_smtp
        self.is_ses = is_ses
        self.is_ses_identity_requested = is_ses_identity_requested
        self.is_ses_identity_verified = is_ses_identity_verified
        self.is_ses_dkim_requested = is_ses_dkim_requested
        self.is_ses_dkim_verified = is_ses_dkim_verified
        self.is_ses_domain_requested = is_ses_domain_requested
        self.is_ses_domain_verified = is_ses_domain_verified
        self.is_reply_proxy = is_reply_proxy
        

    # Primary Keys
    email_config_id = Column(String(36), primary_key=True)

    # Foreign Keys
    account_id = Column(String(36), ForeignKey('account.account_id'))
    credentials_id = Column(String(36), ForeignKey('credentials.credentials_id'))
    email_server_id = Column(String(36), ForeignKey('email_server.email_server_id'))

    # Common Columns
    from_full_name = Column(String(64), nullable=False)
    from_address = Column(String(64), nullable=False)
    # reply_to_address = Column(String(64), nullable=False)
    is_sendgrid = Column(Boolean, nullable=False, server_default=false())
    is_sendgrid_domain_verified = Column(Boolean, nullable=False, server_default=false())
    is_smtp = Column(Boolean, nullable=False, server_default=false())
    is_ses = Column(Boolean, nullable=False, server_default=false())
    is_ses_identity_requested = Column(Boolean, nullable=False, server_default=false())
    is_ses_identity_verified = Column(Boolean, nullable=False, server_default=false())
    is_ses_dkim_requested = Column(Boolean, nullable=False, server_default=false())
    is_ses_dkim_verified = Column(Boolean, nullable=False, server_default=false())
    is_ses_domain_verified = Column(Boolean, nullable=False, server_default=false())
    is_email_forward = Column(Boolean, nullable=False, server_default=false())
    is_email_forwarding_rule_verified = Column(Boolean, nullable=False, server_default=false())
    is_reply_proxy = Column(Boolean, nullable=False, server_default=false())

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    # updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    credentials = relationship('Credentials', backref=backref('email_config', uselist=False), uselist=False, lazy=True)
    email_server = relationship('Email_server', uselist=False, lazy=True)

class Janium_campaign(Base):
    __tablename__ = 'janium_campaign'
    unassigned_janium_campaign_id = '65c96bb2-0c32-4858-a913-ca0cd902f1fe'

    def __init__(self, janium_campaign_id, ulinc_config_id, email_config_id, janium_campaign_name, janium_campaign_description, is_messenger, is_reply_in_email_thread, queue_start_time, queue_end_time):
        self.janium_campaign_id = janium_campaign_id
        self.ulinc_config_id = ulinc_config_id
        self.email_config_id = email_config_id
        self.janium_campaign_name = janium_campaign_name
        self.janium_campaign_description = janium_campaign_description
        self.is_messenger = is_messenger
        self.is_reply_in_email_thread = is_reply_in_email_thread
        self.queue_start_time = queue_start_time
        self.queue_end_time = queue_end_time

    # Primary Keys
    janium_campaign_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    # account_id = Column(String(36), ForeignKey('account.account_id'), nullable=False)
    ulinc_config_id = Column(String(36), ForeignKey('ulinc_config.ulinc_config_id'), nullable=False)
    email_config_id = Column(String(36), ForeignKey('email_config.email_config_id'), nullable=False) # Insert dummy value if using account email_config

    # Common Columns
    janium_campaign_name = Column(String(512), nullable=False)
    janium_campaign_description = Column(String(512), nullable=True)
    is_messenger = Column(Boolean, nullable=False, server_default=false())
    is_reply_in_email_thread = Column(Boolean, nullable=False, server_default=false())
    queue_start_time = Column(DateTime, nullable=False)
    queue_end_time = Column(DateTime, nullable=False)

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    # updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    # contacts = relationship('Contact', backref=backref('contact_janium_campaign', uselist=False), uselist=True, lazy='dynamic')
    ulinc_campaigns = relationship('Ulinc_campaign', backref=backref('parent_janium_campaign', uselist=False), uselist=True, lazy='dynamic')
    janium_campaign_steps = relationship('Janium_campaign_step', backref=backref('parent_janium_campaign', uselist=False), uselist=True, lazy='dynamic')
    email_config = relationship('Email_config', backref=backref('email_config_janium_campaign', uselist=False), uselist=False, lazy=True)

    def is_active(self):
        if self.effective_start_date <= datetime.utcnow() <= self.effective_end_date:
            return True
        return False

    def get_utc_effective_dates(self):
        return {"start": self.effective_start_date, "end": self.effective_end_date}

    def get_utc_queue_times(self):
        return {"start": self.queue_start_time, "end": self.queue_end_time}

    def generate_random_timestamp_in_queue_interval(self):
        now = datetime.utcnow()
        queue_start_time = datetime(now.year, now.month, now.day, self.queue_start_time.hour, self.queue_start_time.minute, 00)
        queue_end_time = datetime(now.year, now.month, now.day, self.queue_end_time.hour, self.queue_end_time.minute, 00)
        if queue_end_time > now:
            if queue_start_time > now:
                sec_to_add = random.randint(int((queue_start_time - now).total_seconds()), int((queue_end_time - now).total_seconds()))
            else:
                sec_to_add = random.randint(1, int((queue_end_time - now).total_seconds()))
            return now + timedelta(seconds=sec_to_add)
        else:
            return None

    def get_steps(self):
        steps = []
        for step in self.janium_campaign_steps:
            steps.append(
                {
                    "janium_campaign_step_id": step.janium_campaign_step_id,
                    "janium_campaign_id": step.janium_campaign_id,
                    "janium_campaign_step_type_id": step.janium_campaign_step_type_id,
                    "janium_campaign_step_delay": step.janium_campaign_step_delay,
                    "janium_campaign_step_body": step.janium_campaign_step_body,
                    "janium_campaign_step_subject": step.janium_campaign_step_subject
                }
            )
        steps = sorted(steps, key = lambda item: item['janium_campaign_step_delay'])
        return steps
    
    def get_ulinc_campaigns(self):
        ulinc_campaigns = []
        for uc in self.ulinc_campaigns:
            ulinc_campaigns.append(
                {
                    "ulinc_campaign_id": uc.ulinc_campaign_id,
                    "ulinc_campaign_name": uc.ulinc_campaign_name,
                    "ulinc_ulinc_campaign_id": uc.ulinc_ulinc_campaign_id,
                    "ulinc_is_active": uc.ulinc_is_active,
                    "parent_janium_campaign_id": self.janium_campaign_id,
                    "parent_janium_campaign_name": self.janium_campaign_name
                }
            )
        return sorted(ulinc_campaigns, key = lambda item: item['ulinc_campaign_name'])
    
    def get_total_num_contacts(self):
        res = 0
        for ulinc_campaign in self.ulinc_campaigns:
            res += ulinc_campaign.get_total_num_contacts()
        return res
    
    def get_total_num_connections(self):
        res = 0
        for ulinc_campaign in self.ulinc_campaigns:
            res += ulinc_campaign.get_total_num_connections()
        return res
    
    def get_total_num_responses(self):
        res = 0
        for ulinc_campaign in self.ulinc_campaigns:
            res += ulinc_campaign.get_total_num_responses()
        return res

    
    def get_contacts(self):
        contacts_list = []
        for ulinc_campaign in self.ulinc_campaigns:
            contacts_list += ulinc_campaign.get_contacts()
        contact_list = sorted(contacts_list, key = lambda item: item['full_name'])
        return contact_list
    
    def get_dte_new_connections(self):
        dte_nc_list = []
        for ulinc_campaign in self.ulinc_campaigns:
            dte_nc_list += ulinc_campaign.get_dte_new_connections()
        return sorted(dte_nc_list, key = lambda item: item['connection_date'], reverse=True)
    
    def get_dte_new_messages(self):
        dte_nm_list = []
        for ulinc_campaign in self.ulinc_campaigns:
            dte_nm_list += ulinc_campaign.get_dte_new_messages()
        return sorted(dte_nm_list, key = lambda item: item['msg_timestamp'], reverse=True)
    
    def get_dte_vm_tasks(self):
        dte_vmt_list = []
        for ulinc_campaign in self.ulinc_campaigns:
            dte_vmt_list += ulinc_campaign.get_dte_vm_tasks()
        return sorted(dte_vmt_list, key = lambda item: item['connection_date'], reverse=True)
        
    def get_summary_data(self):
        sql_statement = text(
            "   select 'new_connections' as action_type, \
                count(distinct case when act.action_type_id = 1 and datediff(now(), act.date_added) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 1 and datediff(now(), act.date_added) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 1 and datediff(now(), act.date_added) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 1 and datediff(now(), act.date_added) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 1 then co.contact_id end) as total \
            from janium_campaign jca \
            inner join contact co on co.janium_campaign_id = jca.janium_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where jca.janium_campaign_id = '{janium_campaign_id}' \
            UNION \
            select 'li_responses' as action_type, \
                count(distinct case when act.action_type_id = 2 and datediff(now(), act.action_timestamp) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 2 and datediff(now(), act.action_timestamp) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 2 and datediff(now(), act.action_timestamp) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 2 and datediff(now(), act.action_timestamp) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 2 then co.contact_id end) as total \
            from janium_campaign jca \
            inner join contact co on co.janium_campaign_id = jca.janium_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where jca.janium_campaign_id = '{janium_campaign_id}' \
            UNION \
            select 'li_messages_sent' as action_type, \
                count(distinct case when act.action_type_id = 3 and datediff(now(), act.action_timestamp) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 3 and datediff(now(), act.action_timestamp) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 3 and datediff(now(), act.action_timestamp) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 3 and datediff(now(), act.action_timestamp) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 3 then co.contact_id end) as total \
            from janium_campaign jca \
            inner join contact co on co.janium_campaign_id = jca.janium_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where jca.janium_campaign_id = '{janium_campaign_id}' \
            UNION \
            select 'email_responses' as action_type, \
                count(distinct case when act.action_type_id = 6 and datediff(now(), act.action_timestamp) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 6 and datediff(now(), act.action_timestamp) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 6 and datediff(now(), act.action_timestamp) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 6 and datediff(now(), act.action_timestamp) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 6 then co.contact_id end) as total \
            from janium_campaign jca \
            inner join contact co on co.janium_campaign_id = jca.janium_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where jca.janium_campaign_id = '{janium_campaign_id}' \
            UNION \
            select 'email_messages_sent' as action_type, \
                count(distinct case when act.action_type_id = 4 and datediff(now(), act.action_timestamp) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 4 and datediff(now(), act.action_timestamp) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 4 and datediff(now(), act.action_timestamp) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 4 and datediff(now(), act.action_timestamp) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 4 then co.contact_id end) as total \
            from janium_campaign jca \
            inner join contact co on co.janium_campaign_id = jca.janium_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where jca.janium_campaign_id = '{janium_campaign_id}';".format(janium_campaign_id=self.janium_campaign_id)
        )

        summary_data = {}
        result = db.engine.execute(sql_statement)
        for line in result:
            summary_data[line[0]] = {
                "24h": line[1],
                "72h": line[2],
                "week": line[3],
                "month": line[4],
                "total": line[5]
            }
        # print(summary_data)
        return summary_data
    
    def get_data_enrichment_targets(self):
        targets =[]
        if campaign_steps := self.janium_campaign_steps.filter(Janium_campaign_step.janium_campaign_step_type_id == 4).order_by(Janium_campaign_step.janium_campaign_step_delay).all():
            contacts = []
            for ulinc_campaign in self.ulinc_campaigns:
                contacts += ulinc_campaign.get_data_enrichment_targets()
            
            for contact in contacts:
                contact_dict = contact._asdict()
                cnxn_req_action = contact_dict['Action']
                contact = contact_dict['Contact']
                if da_action := contact.actions.filter(Action.action_type_id == 22).first():
                    continue
                else:
                    if (networkdays(cnxn_req_action.action_timestamp, datetime.utcnow()) - 1) >= (campaign_steps[0].janium_campaign_step_delay - 1):
                        targets.append(contact)
        return targets

    def get_email_targets(self):
        email_targets_list = []
        targets = []
        campaign_steps = self.janium_campaign_steps.order_by(Janium_campaign_step.janium_campaign_step_delay.asc()).all()
        for uc in self.ulinc_campaigns:
            targets += uc.get_email_targets()

        for contact in targets:
            contact_dict = contact._asdict()
            action = contact_dict['Action']
            contact = contact_dict['Contact']
            emails = contact.get_emails()
            if len(emails) and action.action_type_id in [1,19]:
                add_contact = False
                cnxn_action = action if action.action_type_id == 1 else None
                cnxn_req_action = action if action.action_type_id == 19 and not db.session.query(Action).filter(Action.contact_id == contact.contact_id).filter(Action.action_type_id == 1).first() else None
                continue_campaign_action = contact.actions.filter(Action.action_type_id == 14).order_by(Action.action_timestamp.desc()).first()
                previous_received_messages = contact.actions.filter(Action.action_type_id.in_([2, 6, 11, 21])).order_by(Action.action_timestamp.desc()).all()

                if previous_received_messages:
                    if continue_campaign_action:
                        if previous_received_messages[0].action_timestamp > continue_campaign_action.action_timestamp:
                            continue
                    else:
                        continue
                if cnxn_action:
                    prev_actions = contact.actions.filter(Action.action_type_id.in_([3,4])).filter(Action.action_timestamp >= cnxn_action.action_timestamp).order_by(Action.action_timestamp.desc()).all()
                    sent_emails = [sent_email for sent_email in prev_actions if prev_actions and sent_email.action_type_id == 4]
                    num_sent_emails = len(sent_emails) if sent_emails else 0
                    last_sent_email = sent_emails[0] if sent_emails else None

                    if continue_campaign_action:
                        cnxn_timestamp = cnxn_action.action_timestamp
                        if last_sent_email:
                            days_to_add = networkdays(last_sent_email.action_timestamp, continue_campaign_action.action_timestamp) - 1
                        else:
                            days_to_add = networkdays(previous_received_messages[0].action_timestamp, continue_campaign_action.action_timestamp) - 1
                        while days_to_add > 0:
                            cnxn_timestamp += timedelta(days=1)
                            if cnxn_timestamp.weekday() >= 5: # sunday = 6
                                continue
                            days_to_add -= 1
                    else:
                        cnxn_timestamp = cnxn_action.action_timestamp
                    
                    day_diff = networkdays(cnxn_timestamp, datetime.utcnow()) - 1

                    post_cnxn_steps = [step for step in campaign_steps if step.janium_campaign_step_type_id in [1,2]]
                    post_cnxn_email_steps = [step for step in post_cnxn_steps if step.janium_campaign_step_type_id == 2]
                    prev_email_actions = [action for action in prev_actions if action.action_type_id == 4]
                    prev_email_messages = [message.action_message for message in prev_email_actions]
                    for i, step in enumerate(post_cnxn_email_steps):
                        if step.janium_campaign_step_body in prev_email_messages:
                            continue
                        step_index = post_cnxn_steps.index(step)
                        if step.janium_campaign_step_delay <= day_diff:
                            if num_sent_emails < i + 1:
                                if i == 0:
                                    body = step.janium_campaign_step_body
                                    subject = step.janium_campaign_step_subject
                                    add_contact = True
                                    break
                                else:
                                    if (networkdays(prev_actions[0].action_timestamp, datetime.utcnow()) - 1) >= (step.janium_campaign_step_delay - post_cnxn_steps[step_index-1].janium_campaign_step_delay):
                                        if (networkdays(prev_email_actions[0].action_timestamp, datetime.utcnow()) - 1) >= (step.janium_campaign_step_delay - post_cnxn_email_steps[i-1].janium_campaign_step_delay):
                                            body = step.janium_campaign_step_body
                                            subject = step.janium_campaign_step_subject
                                            add_contact = True
                                            break
                elif cnxn_req_action:                    
                    prev_actions = contact.actions.filter(Action.action_type_id.in_([3,4])).filter(Action.action_timestamp >= cnxn_req_action.action_timestamp).order_by(Action.action_timestamp.desc()).all()
                    sent_emails = [sent_email for sent_email in prev_actions if prev_actions and sent_email.action_type_id == 4]
                    num_sent_emails = len(sent_emails) if sent_emails else 0
                    last_sent_email = sent_emails[0] if sent_emails else None

                    day_diff = networkdays(cnxn_req_action.action_timestamp, datetime.utcnow()) - 1

                    pre_cnxn_steps = [step for step in campaign_steps if step.janium_campaign_step_type_id == 4]
                    for i, step in enumerate(pre_cnxn_steps):
                        add_contact = False
                        body = step.janium_campaign_step_body
                        subject = step.janium_campaign_step_subject
                        if step.janium_campaign_step_delay <= day_diff:
                            if num_sent_emails < i + 1:
                                if i == 0:
                                    add_contact = True
                                    break
                                else:
                                    if (networkdays(prev_actions[0].action_timestamp, datetime.utcnow()) - 1) >= (step.janium_campaign_step_delay - pre_cnxn_steps[i-1].janium_campaign_step_delay):
                                        add_contact = True
                                        break

                if add_contact:
                    email_targets_list.append(
                        {
                            "janium_campaign_id": self.janium_campaign_id,
                            "email_config_id": self.email_config_id,
                            "contact_id": contact.contact_id,
                            "contact_first_name": contact.contact_info['ulinc']['first_name'],
                            "contact_full_name": str(contact.contact_info['ulinc']['first_name'] + ' ' + contact.contact_info['ulinc']['last_name']),
                            "contact_email": emails[0],
                            "email_subject": subject,
                            "email_body": body,
                            "action": action.action_type_id
                        }
                    )
        # def is_boxerman(x):
        #     if x['contact_full_name'] == 'Aaron Boxerman':
        #         return True
        #     else:
        #         return False
        # return list(filter(is_boxerman, email_targets_list))

        # return email_targets_list
        return sorted(email_targets_list, key = lambda item: item['contact_first_name'])
    

    def get_li_message_targets(self):
        li_message_targets_list = []
        if campaign_steps := self.janium_campaign_steps.order_by(Janium_campaign_step.janium_campaign_step_delay).all():
            targets = []
            for uc in self.ulinc_campaigns:
                targets += uc.get_li_message_targets()

            for contact in targets:
                contact_dict = contact._asdict()
                action = contact_dict['Action']
                contact = contact_dict['Contact']
                if action.action_type_id == 1:
                    add_contact = False
                    cnxn_action = action
                    # cnxn_req_action = contact.actions.filter(Action.action_type_id == action.action_type_id).order_by(Action.action_timestamp.desc()).first()
                    continue_campaign_action = contact.actions.filter(Action.action_type_id == 14).order_by(Action.action_timestamp.desc()).first()
                    previous_received_messages = contact.actions.filter(Action.action_type_id.in_([2, 6, 11, 21])).order_by(Action.action_timestamp.desc()).all()

                    if previous_received_messages:
                        if continue_campaign_action:
                            if previous_received_messages[0].action_timestamp > continue_campaign_action.action_timestamp:
                                continue
                        else:
                            continue
                    if cnxn_action and cnxn_action.action_type_id == 1:
                        prev_actions = contact.actions.filter(Action.action_type_id.in_([3,4])).filter(Action.action_timestamp >= cnxn_action.action_timestamp).order_by(Action.action_timestamp.desc()).all()
                        sent_li_messages = contact.actions.filter(Action.action_type_id == 3).filter(Action.action_timestamp >= cnxn_action.action_timestamp).order_by(Action.action_timestamp.desc()).all()
                        num_sent_li_messages = len(sent_li_messages) if sent_li_messages else 0
                        last_sent_li_message = sent_li_messages[0] if sent_li_messages else None

                        if continue_campaign_action:
                            cnxn_timestamp = cnxn_action.action_timestamp
                            if last_sent_li_message:
                                days_to_add = networkdays(last_sent_li_message.action_timestamp, continue_campaign_action.action_timestamp) - 1
                            else:
                                days_to_add = networkdays(previous_received_messages[0].action_timestamp, continue_campaign_action.action_timestamp) - 1
                            while days_to_add > 0:
                                cnxn_timestamp += timedelta(days=1)
                                if cnxn_timestamp.weekday() >= 5: # sunday = 6
                                    continue
                                days_to_add -= 1
                        else:
                            cnxn_timestamp = cnxn_action.action_timestamp
                        
                        day_diff = networkdays(cnxn_timestamp, datetime.utcnow()) - 1


                        post_cnxn_steps = [step for step in campaign_steps if step.janium_campaign_step_type_id in [1,2]]
                        post_cnxn_li_steps = [step for step in post_cnxn_steps if step.janium_campaign_step_type_id == 1]
                        prev_li_actions = [action for action in prev_actions if action.action_type_id == 3]
                        prev_li_messages = [str(message.action_message).strip().replace('\r', '').replace('\n', '') for message in prev_li_actions]
                        for i, step in enumerate(post_cnxn_li_steps):
                            if str(step.janium_campaign_step_body).strip().replace('\r', '').replace('\n', '') in prev_li_messages:
                                continue
                            step_index = post_cnxn_steps.index(step)
                            if step.janium_campaign_step_delay <= day_diff:
                                if num_sent_li_messages < i + 1:
                                    if i == 0:
                                        body = step.janium_campaign_step_body
                                        add_contact = True
                                        break
                                    else:
                                        if (networkdays(prev_actions[0].action_timestamp, datetime.utcnow()) - 1) >= (step.janium_campaign_step_delay - post_cnxn_steps[step_index-1].janium_campaign_step_delay):
                                            if (networkdays(prev_li_actions[0].action_timestamp, datetime.utcnow()) - 1) >= (step.janium_campaign_step_delay - post_cnxn_li_steps[i-1].janium_campaign_step_delay):
                                                body = step.janium_campaign_step_body
                                                add_contact = True
                                                break

                    if add_contact:
                        li_message_targets_list.append(
                            {
                                "janium_campaign_id": self.janium_campaign_id,
                                "contact_id": contact.contact_id,
                                "contact_ulinc_id": contact.get_short_ulinc_id(self.janium_campaign_ulinc_config.ulinc_client_id),
                                "contact_first_name": contact.contact_info['ulinc']['first_name'],
                                "contact_full_name": str(contact.contact_info['ulinc']['first_name'] + ' ' + contact.contact_info['ulinc']['last_name']),
                                "message_body": body,
                                "ulinc_ulinc_campaign_id": contact.ulinc_ulinc_campaign_id,
                                "cookie_usr": self.janium_campaign_ulinc_config.cookie.cookie_json_value['usr'],
                                "cookie_pwd": self.janium_campaign_ulinc_config.cookie.cookie_json_value['pwd'],
                                "ulinc_client_id": self.janium_campaign_ulinc_config.ulinc_client_id
                            }
                        )
        # def is_boxerman(x):
        #     if x['contact_full_name'] == 'Keith Lovegrove':
        #         return True
        #     else:
        #         return False
        # return list(filter(is_boxerman, li_message_targets_list))

        # return sorted(li_message_targets_list, key = lambda item: item['contact_first_name'])
        return sorted(li_message_targets_list, key = lambda item: item['contact_first_name'])


class Janium_campaign_step(Base):
    __tablename__ = 'janium_campaign_step'

    def __init__(self, janium_campaign_step_id, janium_campaign_id, janium_campaign_step_type_id,
                       janium_campaign_step_delay, janium_campaign_step_body,janium_campaign_step_subject,
                       queue_start_time, queue_end_time):
        self.janium_campaign_step_id = janium_campaign_step_id
        self.janium_campaign_id = janium_campaign_id
        self.janium_campaign_step_type_id = janium_campaign_step_type_id
        # self.is_active = is_active
        self.janium_campaign_step_delay = janium_campaign_step_delay
        self.janium_campaign_step_body = janium_campaign_step_body
        self.janium_campaign_step_subject = janium_campaign_step_subject
        self.queue_start_time = queue_start_time
        self.queue_end_time = queue_end_time
        # self.updated_by = updated_by

    # Primary Keys
    janium_campaign_step_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    janium_campaign_id = Column(String(36), ForeignKey('janium_campaign.janium_campaign_id'), nullable=False)
    janium_campaign_step_type_id = Column(Integer, ForeignKey('janium_campaign_step_type.janium_campaign_step_type_id'), nullable=False)

    # Common Columns
    # is_active = Column(Boolean, nullable=False, server_default=true())
    janium_campaign_step_delay = Column(Integer, nullable=False)
    janium_campaign_step_body = Column(Text, nullable=True)
    janium_campaign_step_subject = Column(String(1000), nullable=True)
    queue_start_time = Column(DateTime, nullable=False)
    queue_end_time = Column(DateTime, nullable=False)

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    # updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    janium_campaign_step_type = relationship('Janium_campaign_step_type', uselist=False, lazy=True)

class Ulinc_campaign(Base):
    __tablename__ = 'ulinc_campaign'
    unassigned_ulinc_campaign_id = '943c18f3-74c8-45cf-a396-1ddc89c6b9d2'

    def __init__(self, ulinc_campaign_id, ulinc_config_id, janium_campaign_id, ulinc_campaign_name, ulinc_is_active, ulinc_ulinc_campaign_id, ulinc_is_messenger, ulinc_messenger_origin_message=None, connection_request_message=None):
        self.ulinc_campaign_id = ulinc_campaign_id
        self.ulinc_config_id = ulinc_config_id
        self.janium_campaign_id = janium_campaign_id
        self.ulinc_campaign_name = ulinc_campaign_name
        self.ulinc_is_active = ulinc_is_active
        self.ulinc_ulinc_campaign_id = ulinc_ulinc_campaign_id
        self.ulinc_is_messenger = ulinc_is_messenger
        self.messenger_origin_message = ulinc_messenger_origin_message
        self.connection_request_message = connection_request_message
        # self.updated_by = updated_by

    # Primary Keys
    ulinc_campaign_id = Column(String(36), primary_key=True)
    
    # Foreign Keys
    ulinc_config_id = Column(String(36), ForeignKey('ulinc_config.ulinc_config_id'), nullable=False)
    janium_campaign_id = Column(String(36), ForeignKey('janium_campaign.janium_campaign_id'), nullable=False)

    # Common Columns
    ulinc_campaign_name = Column(String(512), nullable=False)
    ulinc_is_active = Column(Boolean, nullable=False, server_default=false())
    ulinc_ulinc_campaign_id = Column(String(16), nullable=False)
    ulinc_is_messenger = Column(Boolean, nullable=False, server_default=false())
    connection_request_message = Column(Text, nullable=True)
    messenger_origin_message = Column(Text, nullable=True)

    # Table Metadata    
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    # updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    contacts = relationship('Contact', backref=backref('contact_ulinc_campaign', uselist=False), lazy='dynamic')

    def get_summary_data(self):
        sql_statement = text(
            "   select 'new_connections' as action_type, \
                count(distinct case when act.action_type_id = 1 and datediff(now(), act.date_added) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 1 and datediff(now(), act.date_added) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 1 and datediff(now(), act.date_added) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 1 and datediff(now(), act.date_added) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 1 then co.contact_id end) as total \
            from ulinc_campaign uc \
            inner join contact co on co.ulinc_campaign_id = uc.ulinc_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where uc.ulinc_campaign_id = '{ulinc_campaign_id}' \
            UNION \
            select 'li_responses' as action_type, \
                count(distinct case when act.action_type_id = 2 and datediff(now(), act.action_timestamp) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 2 and datediff(now(), act.action_timestamp) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 2 and datediff(now(), act.action_timestamp) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 2 and datediff(now(), act.action_timestamp) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 2 then co.contact_id end) as total \
            from ulinc_campaign uc \
            inner join contact co on co.ulinc_campaign_id = uc.ulinc_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where uc.ulinc_campaign_id = '{ulinc_campaign_id}' \
            UNION \
            select 'li_messages_sent' as action_type, \
                count(distinct case when act.action_type_id = 3 and datediff(now(), act.action_timestamp) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 3 and datediff(now(), act.action_timestamp) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 3 and datediff(now(), act.action_timestamp) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 3 and datediff(now(), act.action_timestamp) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 3 then co.contact_id end) as total \
            from ulinc_campaign uc \
            inner join contact co on co.ulinc_campaign_id = uc.ulinc_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where uc.ulinc_campaign_id = '{ulinc_campaign_id}' \
            UNION \
            select 'email_responses' as action_type, \
                count(distinct case when act.action_type_id = 6 and datediff(now(), act.action_timestamp) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 6 and datediff(now(), act.action_timestamp) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 6 and datediff(now(), act.action_timestamp) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 6 and datediff(now(), act.action_timestamp) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 6 then co.contact_id end) as total \
            from ulinc_campaign uc \
            inner join contact co on co.ulinc_campaign_id = uc.ulinc_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where uc.ulinc_campaign_id = '{ulinc_campaign_id}' \
            UNION \
            select 'email_messages_sent' as action_type, \
                count(distinct case when act.action_type_id = 4 and datediff(now(), act.action_timestamp) < 2 then co.contact_id end) as 24h, \
                count(distinct case when act.action_type_id = 4 and datediff(now(), act.action_timestamp) < 4 then co.contact_id end) as 72h, \
                count(distinct case when act.action_type_id = 4 and datediff(now(), act.action_timestamp) < 8 then co.contact_id end) as week, \
                count(distinct case when act.action_type_id = 4 and datediff(now(), act.action_timestamp) < 32 then co.contact_id end) as month, \
                count(distinct case when act.action_type_id = 4 then co.contact_id end) as total \
            from ulinc_campaign uc \
            inner join contact co on co.ulinc_campaign_id = uc.ulinc_campaign_id \
            inner join action act on act.contact_id = co.contact_id \
            where uc.ulinc_campaign_id = '{ulinc_campaign_id}';".format(ulinc_campaign_id=self.ulinc_campaign_id)
        )

        summary_data = {}
        result = db.engine.execute(sql_statement)
        for line in result:
            summary_data[line[0]] = {
                "24h": line[1],
                "72h": line[2],
                "week": line[3],
                "month": line[4],
                "total": line[5]
            }
        return summary_data
    
    def get_total_num_contacts(self):
        return self.contacts.count()

    def get_total_num_connections(self):
        return db.session.query(
            Contact, Action
        ).filter(
            Contact.ulinc_campaign_id == self.ulinc_campaign_id
        ).filter(
            Action.contact_id == Contact.contact_id
        ).filter(
            Action.action_type_id == 1
        ).count()
    
    def get_total_num_responses(self):
        return db.session.query(
            Contact, Action
        ).filter(
            Contact.ulinc_campaign_id == self.ulinc_campaign_id
        ).filter(
            Action.contact_id == Contact.contact_id
        ).filter(
            Action.action_type_id.in_([2,6])
        ).count()

    def get_contacts(self):
        contacts_list = []
        for contact in self.contacts:
            contact_info = contact.contact_info['ulinc']
            contacts_list.append(
                {
                    "contact_id": contact.contact_id,
                    "first_name": contact_info['first_name'],
                    "scrubbed_first_name": None if "scrubbed_first_name" not in contact_info else contact_info['scrubbed_first_name'],
                    "last_name": contact_info['last_name'],
                    "full_name": str(contact_info['first_name'] + " " + contact_info['last_name']),
                    "title": contact_info['title'],
                    "company": contact_info['company'],
                    "scrubbed_company": None if "scrubbed_company" not in contact_info else contact_info['scrubbed_company'],
                    "location": contact_info['location'],
                    "scrubbed_location": None if "scrubbed_location" not in contact_info else contact_info['scrubbed_location'],
                    "email": contact_info['email'],
                    "phone": contact_info['phone'],
                    "li_profile_url": contact_info['li_profile_url'] if contact_info['li_profile_url'] else contact_info['li_salesnav_profile_url'],
                    "ulinc_campaign_name": self.ulinc_campaign_name
                }
            )
        return contacts_list
    
    def get_dte_new_connections(self):
        new_connections_list = []

        query_result = db.session.query(
                Contact, Action
            ).filter(
                Contact.ulinc_campaign_id == self.ulinc_campaign_id
            ).filter(
                Action.contact_id == Contact.contact_id
            ).filter(
                and_(Action.action_type_id.notin_([2,6,8,9,11]), Action.action_type_id.in_([1]))
            ).order_by(
                Contact.contact_id, Action.action_timestamp.desc()
            ).all()
        for item in query_result:
            item_dict = item._asdict()
            cnxn_action = item_dict['Action']
            contact = item_dict['Contact']
            if 0 <= networkdays(cnxn_action.action_timestamp, datetime.utcnow()) - 1 <= 2:
                new_connections_list.append(
                    {
                        "contact_id": contact.contact_id,
                        "full_name": contact.contact_info['ulinc']['first_name'] + ' ' + contact.contact_info['ulinc']['last_name'],
                        "li_profile_url": contact.contact_info['ulinc']['li_profile_url'] if contact.contact_info['ulinc']['li_profile_url'] else contact.contact_info['ulinc']['li_salesnav_profile_url'],
                        "title": contact.contact_info['ulinc']['title'],
                        "company": contact.contact_info['ulinc']['company'],
                        "location": contact.contact_info['ulinc']['location'],
                        "ulinc_campaign_id": self.ulinc_campaign_id,
                        "ulinc_campaign_name": self.ulinc_campaign_name,
                        "janium_campaign_id": self.parent_janium_campaign.janium_campaign_id,
                        "janium_campaign_name": self.parent_janium_campaign.janium_campaign_name,
                        "connection_date": cnxn_action.action_timestamp,
                        "is_clicked": True if contact.actions.filter(Action.action_type_id == 8).first() else False,
                        "is_dqd": True if contact.actions.filter(Action.action_type_id == 11).first() else False
                    }
                )
        return sorted(new_connections_list, key = lambda item: item['connection_date'], reverse=True)
    
    def get_dte_new_messages(self):
        new_messages_list = []
        prev_contact_id = ''

        query_result = db.session.query(
                Contact, Action
            ).filter(
                Contact.ulinc_campaign_id == self.ulinc_campaign_id
            ).filter(
                Action.contact_id == Contact.contact_id
            ).filter(
                and_(Action.action_type_id.notin_([11]), Action.action_type_id.in_([2,6]))
            ).order_by(
                Contact.contact_id, Action.action_timestamp.desc()
            ).all()
        for item in query_result:
            item_dict = item._asdict()
            msg_action = item_dict['Action']
            contact = item_dict['Contact']
            if 0 <= networkdays(msg_action.action_timestamp, datetime.utcnow()) - 1 <= 2:
                if contact.contact_id == prev_contact_id:
                    continue
                prev_contact_id = contact.contact_id
                new_messages_list.append(
                    {
                        "contact_id": contact.contact_id,
                        "full_name": contact.contact_info['ulinc']['first_name'] + ' ' + contact.contact_info['ulinc']['last_name'],
                        "li_profile_url": contact.contact_info['ulinc']['li_profile_url'] if contact.contact_info['ulinc']['li_profile_url'] else contact.contact_info['ulinc']['li_salesnav_profile_url'],
                        "title": contact.contact_info['ulinc']['title'],
                        "company": contact.contact_info['ulinc']['company'],
                        "location": contact.contact_info['ulinc']['location'],
                        "ulinc_campaign_id": self.ulinc_campaign_id,
                        "ulinc_campaign_name": self.ulinc_campaign_name,
                        "janium_campaign_id": self.parent_janium_campaign.janium_campaign_id,
                        "janium_campaign_name": self.parent_janium_campaign.janium_campaign_name,
                        "msg_timestamp": msg_action.action_timestamp,
                        "msg_type": "email" if msg_action.action_type_id == 6 else "li_message",
                        "is_clicked": True if contact.actions.filter(Action.action_type_id == 9).first() else False,
                        "is_dqd": True if contact.actions.filter(Action.action_type_id == 11).first() else False
                    }
                )
        return sorted(new_messages_list, key = lambda item: item['msg_timestamp'], reverse=True)
    
    def get_dte_vm_tasks(self):
        vm_tasks_list = []
        janium_campaign = self.parent_janium_campaign
        if janium_campaign.janium_campaign_id != Janium_campaign.unassigned_janium_campaign_id:
            if janium_campaign_steps := janium_campaign.janium_campaign_steps.order_by(Janium_campaign_step.janium_campaign_step_delay.desc()).all():
                if last_step := janium_campaign_steps[0]:
                    query_result = db.session.query(
                        Contact, Action
                    ).filter(
                        Contact.ulinc_campaign_id == self.ulinc_campaign_id
                    ).filter(
                        Action.contact_id == Contact.contact_id
                    ).filter(
                        and_(Action.action_type_id.notin_([2,6,11]), Action.action_type_id.in_([1]))
                    ).order_by(
                        Contact.contact_id, Action.action_timestamp.desc()
                    ).all()
                    for item in query_result:
                        item_dict = item._asdict()
                        cnxn_action = item_dict['Action']
                        contact = item_dict['Contact']
                        if last_step.janium_campaign_step_delay <= networkdays(cnxn_action.action_timestamp, datetime.utcnow()) - 1 <= last_step.janium_campaign_step_delay + 5:
                            vm_tasks_list.append(
                                {
                                    "contact_id": contact.contact_id,
                                    "full_name": contact.contact_info['ulinc']['first_name'] + ' ' + contact.contact_info['ulinc']['last_name'],
                                    "li_profile_url": contact.contact_info['ulinc']['li_profile_url'] if contact.contact_info['ulinc']['li_profile_url'] else contact.contact_info['ulinc']['li_salesnav_profile_url'],
                                    "title": contact.contact_info['ulinc']['title'],
                                    "company": contact.contact_info['ulinc']['company'],
                                    "location": contact.contact_info['ulinc']['location'],
                                    "phone": contact.contact_info['ulinc']['phone'],
                                    "ulinc_campaign_id": self.ulinc_campaign_id,
                                    "ulinc_campaign_name": self.ulinc_campaign_name,
                                    "janium_campaign_id": janium_campaign.janium_campaign_id,
                                    "janium_campaign_name": janium_campaign.janium_campaign_name,
                                    "connection_date": cnxn_action.action_timestamp,
                                    "is_clicked": True if contact.actions.filter(Action.action_type_id == 10).first() else False,
                                    "is_dqd": True if contact.actions.filter(Action.action_type_id == 11).first() else False
                                }
                            )
        return sorted(vm_tasks_list, key = lambda item: item['connection_date'], reverse=True)
    
    def get_data_enrichment_targets(self):
        return db.session.query(
            Contact, Action
        ).filter(
            Contact.ulinc_campaign_id == self.ulinc_campaign_id
        ).filter(
            Action.contact_id == Contact.contact_id
        ).filter(
            Action.action_type_id == 19
        ).filter(
            Contact.contact_info['ulinc']['li_profile_url'] != cast(text("'null'"), JSON)
        ).filter(
            ~Contact.actions.any(Action.action_type_id.in_([1,2,6,11,15,7]))
        ).order_by(
            Contact.contact_id, Action.action_timestamp.desc()
        ).all()

    def get_email_targets(self):
        return db.session.query(
            Contact, Action
        ).filter(
            Contact.ulinc_campaign_id == self.ulinc_campaign_id
        ).filter(
            Contact.contact_id == Action.contact_id
        ).filter(
            ~Contact.actions.any(Action.action_type_id.in_([7,11,15]))
        ).all()
    
    def get_li_message_targets(self):
        return db.session.query(
            Contact, Action
        ).filter(
            Contact.ulinc_campaign_id == self.ulinc_campaign_id
        ).filter(
            Contact.contact_id == Action.contact_id
        ).filter(
            ~Contact.actions.any(Action.action_type_id.in_([7,11]))
        ).all()


class Ulinc_campaign_origin_message(Base):
    __tablename__ = 'ulinc_campaign_origin_message'

    def __init__(self, ulinc_campaign_origin_message_id, ulinc_campaign_id, message, is_messenger=False):
        self.ulinc_campaign_origin_message_id = ulinc_campaign_origin_message_id
        self.ulinc_campaign_id = ulinc_campaign_id
        self.message = message
        self.is_messenger = is_messenger

    ulinc_campaign_origin_message_id = Column(String(36), primary_key=True, nullable=False)
    ulinc_campaign_id = Column(String(36), ForeignKey('ulinc_campaign.ulinc_campaign_id'), nullable=False)
    message = Column(Text, nullable=False)
    is_messenger = Column(Boolean, nullable=False, server_default=false())


class Contact_source(Base):
    __tablename__ = 'contact_source'
    unassigned_contact_source_id = '950e964d-29bd-4ac6-96c4-8b27fadd8dee'

    def __init__(self, contact_source_id, ulinc_config_id, contact_source_type_id, contact_source_json, is_processed=False):
        self.contact_source_id = contact_source_id
        self.ulinc_config_id = ulinc_config_id
        self.contact_source_type_id = contact_source_type_id
        self.contact_source_json = contact_source_json
        self.is_processed = is_processed
    
    # Primary Keys
    contact_source_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    ulinc_config_id = Column(String(36), ForeignKey('ulinc_config.ulinc_config_id'), nullable=False)
    contact_source_type_id = Column(Integer, ForeignKey('contact_source_type.contact_source_type_id'), nullable=False)

    # Common Columns
    contact_source_json = Column(JSON, nullable=False)
    is_processed = Column(Boolean, nullable=False, server_default=false())

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences
    contacts = relationship('Contact', backref=backref('contact_source', uselist=False), lazy=False)

class Contact(Base):
    __tablename__ = 'contact'
    unassigned_contact_id = '9b84cf42-80f5-4cb4-80e6-7da4632b8177'

    def __init__(self, contact_id, contact_source_id, ulinc_campaign_id, ulinc_id, ulinc_ulinc_campaign_id, contact_info, tib_id=None):
        self.contact_id = contact_id
        self.contact_source_id = contact_source_id
        self.ulinc_campaign_id = ulinc_campaign_id
        self.ulinc_id = ulinc_id
        self.ulinc_ulinc_campaign_id = ulinc_ulinc_campaign_id
        self.contact_info = contact_info
        self.tib_id = tib_id

    # Primary Keys
    contact_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    # account_id = Column(String(36), ForeignKey('account.account_id'), nullable=False)
    # janium_campaign_id = Column(String(36), ForeignKey('janium_campaign.janium_campaign_id'), nullable=False)
    ulinc_campaign_id = Column(String(36), ForeignKey('ulinc_campaign.ulinc_campaign_id'), nullable=False)
    contact_source_id = Column(String(36), ForeignKey('contact_source.contact_source_id'), nullable=False)

    # Common Columns
    ulinc_id = Column(String(16), nullable=False)
    ulinc_ulinc_campaign_id = Column(String(16), nullable=False)
    tib_id = Column(String(36), nullable=True)
    contact_info = Column(JSON, nullable=False)

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))

    # SQLAlchemy Relationships and Backreferences
    actions = relationship('Action', backref=backref('contact', uselist=False), uselist=True, lazy='dynamic')
    # info = relationship('Contact_info', uselist=True, lazy='dynamic')

    def is_messaging_task_valid(self):
        utc_now = datetime.utcnow()
        if stop_actions := self.actions.filter(Action.action_type_id.in_([2,6,7,11])).filter(Action.action_timestamp >= utc_now - timedelta(hours=18)).order_by(Action.action_timestamp.desc()).all():
            if continue_action := self.actions.filter(Action.action_type_id == 14).filter(Action.action_timestamp >= utc_now - timedelta(hours=18)).first():
                if continue_action.action_timestamp >= stop_actions[0].action_timestamp:
                    return True
                return False
            return False
        return True

    def get_short_ulinc_id(self, ulinc_client_id):
        return str(self.ulinc_id).replace(ulinc_client_id, '')

    def get_emails(self):
        contact_info = self.contact_info
        email_dict = {
            "kendo_work_email": None,
            "ulinc_private_email": None,
            "kendo_private_email": None
        }
        if 'kendo' in contact_info:
            if 'private_email' in contact_info['kendo']:
                email_dict['kendo_private_email'] = contact_info['kendo']['private_email']['value']
            elif 'work_email' in contact_info['kendo']:
                email_dict['kendo_work_email'] = contact_info['kendo']['work_email']['value']
        if 'ulinc' in contact_info:
            email_dict['ulinc_private_email'] = contact_info['ulinc']['email']
        
        ordered_list = [0,0,0]
        ordered_list[0] = email_dict['kendo_work_email']
        ordered_list[1] = email_dict['ulinc_private_email']
        ordered_list[2] = email_dict['kendo_private_email']
        return list(filter(None, ordered_list))
        


class Action(Base):
    __tablename__ = 'action'

    def __init__(self, action_id, contact_id, action_type_id, action_timestamp, action_message, to_email_addr=None, email_message_id=None):
        self.action_id = action_id
        self.contact_id = contact_id
        self.action_type_id = action_type_id
        self.action_timestamp = action_timestamp
        self.action_message = action_message
        self.to_email_addr = to_email_addr
        self.email_message_id = email_message_id

    # Primary Keys
    action_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    contact_id = Column(String(36), ForeignKey('contact.contact_id'), nullable=False)
    action_type_id = Column(Integer, ForeignKey('action_type.action_type_id'), nullable=False)

    # Common Columns
    action_timestamp = Column(DateTime, nullable=True)
    action_message = Column(Text, nullable=True)
    to_email_addr = Column(String(64), nullable=True)
    email_message_id = Column(String(512), nullable=True)

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences
    action_type = relationship('Action_type', uselist=False, lazy=True)

class Dte(Base):
    __tablename__ = 'dte'
    janium_dte_id = '38429485-59e1-4eeb-a4bb-05696ead8e49'
    unassigned_dte_id = 'e18bd1b0-b404-41ac-a5e4-bcb112ced90d'

    def __init__(self, dte_id, dte_name, dte_description, dte_subject, dte_body):
        self.dte_id = dte_id
        self.dte_name = dte_name
        self.dte_description = dte_description
        self.dte_subject = dte_subject
        self.dte_body = dte_body

    # Primary Keys
    dte_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys

    # Common Columns
    dte_name = Column(String(128), nullable=False)
    dte_description = Column(String(256), nullable=True)
    dte_subject = Column(String(512), nullable=False)
    dte_body = Column(Text, nullable=False)

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    # updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)
    # SQLAlchemy Relationships and Backreferences

class Dte_sender(Base):
    __tablename__ = 'dte_sender'
    janium_default_dte_sender_id = 'aecf4b11-7bd4-41e0-9a75-8b457bdbe07a'
    unassigned_dte_sender_id = '70f29ac6-edc0-452b-8d7b-3d3ee87c09f0'

    def __init__(self, dte_sender_id, dte_sender_full_name, dte_sender_from_email):
        self.dte_sender_id = dte_sender_id
        self.dte_sender_full_name = dte_sender_full_name
        self.dte_sender_from_email = dte_sender_from_email
    
    dte_sender_id = Column(String(36), primary_key=True, nullable=False)
    dte_sender_full_name = Column(String(128), nullable=False)
    dte_sender_from_email = Column(String(128), nullable=False)

    is_ses_dkim_requested = Column(Boolean, nullable=False, server_default=false())
    is_ses_dkim_verified = Column(Boolean, nullable=False, server_default=false())
    is_ses_domain_verified = Column(Boolean, nullable=False, server_default=false())


class Email_server(Base):
    __tablename__ = 'email_server'
    gmail_id = '936dce84-b50f-4b72-824f-b01989b20500'

    def __init__(self, email_server_id, email_server_name, smtp_address, smtp_tls_port, smtp_ssl_port, imap_address, imap_ssl_port):
        self.email_server_id = email_server_id
        self.email_server_name = email_server_name
        self.smtp_address = smtp_address
        self.smtp_tls_port = smtp_tls_port
        self.smtp_ssl_port = smtp_ssl_port
        self.imap_address = imap_address
        self.imap_ssl_port = imap_ssl_port

    # Primary Keys
    email_server_id = Column(String(36), primary_key=True)

    # Foreign Keys

    # Common Columns
    email_server_name = Column(String(64), nullable=False)
    smtp_address = Column(String(64), nullable=False)
    smtp_tls_port = Column(Integer, nullable=False)
    smtp_ssl_port = Column(Integer, nullable=False)
    imap_address = Column(String(64), nullable=False)
    imap_ssl_port = Column(Integer, nullable=False)

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences

class Credentials(Base):
    __tablename__ = 'credentials'
    janium_email_app_credentials_id = 'a217fb95-0a28-49ba-a18a-a0298d0b68b3'
    unassigned_credentials_id = '264f534f-d36e-4c3c-9614-9760f47ee0e3'

    def __init__(self, credentials_id, username, password):
        self.credentials_id = credentials_id
        self.username = username
        self.password = password

    # Primary Keys
    credentials_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys

    # Common Columns
    username = Column(String(256), nullable=False)
    password = Column(String(256), nullable=False)

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))

    # SQLAlchemy Relationships and Backreferences

class Cookie(Base):
    __tablename__ = 'cookie'
    unassigned_cookie_id = 'dd0dfdaa-3d58-4d96-85dc-cd68307f528d'

    def __init__(self, cookie_id, cookie_type_id, cookie_json_value):
        self.cookie_id = cookie_id
        self.cookie_type_id = cookie_type_id
        self.cookie_json_value = cookie_json_value

    # Primary Keys
    cookie_id = Column(String(36), primary_key=True)

    # Foreign Keys
    cookie_type_id = Column(Integer, ForeignKey('cookie_type.cookie_type_id'))

    # Common Columns
    cookie_json_value = Column(JSON, nullable=False)

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    # updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    cookie_type = relationship('Cookie_type', uselist=False, lazy=True)


class Cookie_type(Base):
    __tablename__ = 'cookie_type'

    def __init__(self, cookie_type_id, cookie_type_name, cookie_type_description):
        self.cookie_type_id = cookie_type_id
        self.cookie_type_name = cookie_type_name
        self.cookie_type_description = cookie_type_description

    # Primary Keys
    cookie_type_id = Column(Integer, primary_key=True)

    # Foreign Keys

    # Common Columns
    cookie_type_name = Column(String(128), nullable=False)
    cookie_type_description = Column(String(256), nullable=True)
    cookie_type_website_url = Column(String(512), nullable=True)

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences

class Time_zone(Base):
    __tablename__ = 'time_zone'

    def __init__(self, time_zone_id, time_zone_name, time_zone_code):
        self.time_zone_id = time_zone_id
        self.time_zone_name = time_zone_name
        self.time_zone_code = time_zone_code
    
    time_zone_id = Column(String(36), primary_key=True)
    time_zone_name = Column(String(64), nullable=False)
    time_zone_code = Column(String(16), nullable=False)

    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

class Janium_campaign_step_type(Base):
    __tablename__ = 'janium_campaign_step_type'

    def __init__(self, janium_campaign_step_type_id, janium_campaign_step_type_name, janium_campaign_step_type_description):
        self.janium_campaign_step_type_id = janium_campaign_step_type_id
        self.janium_campaign_step_type_name = janium_campaign_step_type_name
        self.janium_campaign_step_type_description = janium_campaign_step_type_description

    # Primary Keys
    janium_campaign_step_type_id = Column(Integer, primary_key=True, nullable=False)

    # Foreign Keys

    # Common Columns
    janium_campaign_step_type_name = Column(String(64), nullable=False)
    janium_campaign_step_type_description = Column(String(512), nullable=False)

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences

class Action_type(Base): # (messenger_origin_message, new_connection_date{backdate contacts})
    __tablename__ = 'action_type'

    def __init__(self, action_type_id, action_type_name, action_type_description):
        self.action_type_id = action_type_id
        self.action_type_name = action_type_name
        self.action_type_description = action_type_description

    # Primary Keys
    action_type_id = Column(Integer, primary_key=True, nullable=False)

    # Foreign Keys

    # Common Columns
    action_type_name = Column(String(64), nullable=False)
    action_type_description = Column(String(512), nullable=False)

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences

class Contact_source_type(Base):
    __tablename__ = 'contact_source_type'

    def __init__(self, contact_source_type_id, contact_source_type_name, contact_source_type_description):
        self.contact_source_type_id = contact_source_type_id
        self.contact_source_type_name = contact_source_type_name
        self.contact_source_type_description = contact_source_type_description
    
    # Primary Keys
    contact_source_type_id = Column(Integer, primary_key=True, nullable=False)

    # Foreign Keys

    # Common Columns
    contact_source_type_name = Column(String(128), nullable=False)
    contact_source_type_description = Column(String(256), nullable=False)

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences




































# class Account_type(Base):
#     __tablename__ = 'account_type'

#     def __init__(self, account_type_id, account_type_name, account_type_description):
#         self.account_type_id = account_type_id
#         self.account_type_name = account_type_name
#         self.account_type_description = account_type_description
    
#     account_type_id = Column(Integer, primary_key=True, nullable=False)
#     account_type_name = Column(String(128), nullable=False)
#     account_type_description = Column(String(256), nullable=False)
#     date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))




# class User_account_map(Base):
#     __tablename__ = 'user_account_map'

#     def __init__(self, user_id, account_id, permission_id):
#         self.user_id = user_id
#         self.account_id = account_id
#         self.permission_id = permission_id

#     user_id = Column(String(36), ForeignKey('user.user_id'), primary_key=True, nullable=False)
#     account_id = Column(String(36), ForeignKey('account.account_id'), primary_key=True, nullable=False)
#     permission_id = Column(String(36), ForeignKey('permission.permission_id'), primary_key=True, nullable=False)

#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     # updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

#     user = relationship('User', back_populates='accounts')
#     account = relationship('Account', back_populates='users')
#     # user = relationship('User', foreign_keys=[user_id])
#     # user = relationship('User', foreign_keys='User_account_map.user_id')
#     # account = relationship('Account', foreign_keys=[account_id])


# class User_proxy_map(Base):
#     __tablename__ = 'user_proxy_map'

#     def __init__(self, user_id, account_id):
#         self.user_id = user_id
#         self.account_id = account_id
    
#     user_id = Column(String(36), ForeignKey('user.user_id'), primary_key=True, nullable=False)
#     account_id = Column(String(36), ForeignKey('account.account_id'), primary_key=True, nullable=False)

#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

#     # user = relationship('User', back_populates='proxy_accounts', foreign_keys=[user_id])
#     # account = relationship('Account', back_populates='proxy_users')
#     # user = relationship('User', foreign_keys=[user_id])
#     # account = relationship('Account', foreign_keys=[account_id])

# class User_permission_map(Base):
#     __tablename__ = 'user_permission_map'

#     def __init__(self, user_id, permission_id):
#         self.user_id = user_id
#         self.permission_id = permission_id
    
#     user_id = Column(String(36), ForeignKey('user.user_id'), primary_key=True, nullable=False)
#     permission_id = Column(String(36), ForeignKey('permission.permission_id'), primary_key=True, nullable=False)

#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

#     # user = relationship('User', back_populates='permissions', foreign_keys=[user_id])
#     # permission = relationship('Permission', back_populates='permission_users')
#     # user = relationship('User', foreign_keys=[user_id])
#     # permission = relationship('Permission', foreign_keys=[permission_id])

# class Permission(Base):
#     __tablename__ = 'permission'
#     default_permission_id = '2e9b5679-134d-4b6e-9a4d-6e14138eab22'

#     def __init__(self, permission_id, permission_name, permission_description, updated_by):
#         self.permission_id = permission_id
#         self.permission_name = permission_name
#         self.permission_description = permission_description
#         self.updated_by = updated_by
    
#     permission_id = Column(String(36), primary_key=True, nullable=False)
#     permission_name = Column(String(64), nullable=False)
#     permission_description = Column(String(512), nullable=False)

#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

#     # users = relationship('User_permission_map', back_populates='permission_user')

# class Permission_hierarchy(Base):
#     __tablename__ = 'permission_hierarchy'

#     def __init__(self, permission_hierarchy_id, parent_permission_id, child_permission_id):
#         self.permission_hierarchy_id = permission_hierarchy_id
#         self.parent_permission_id = parent_permission_id
#         self.child_permission_id = child_permission_id
    
#     permission_hierarchy_id = Column(String(36), primary_key=True, nullable=False)
#     parent_permission_id = Column(String(36), ForeignKey('permission.permission_id'), nullable=False)
#     child_permission_id = Column(String(36), ForeignKey('permission.permission_id'), nullable=False)

#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

#     # users = relationship('User_permission_map', back_populates='permission_user')


# class Account_group(Base):
#     __tablename__ = 'account_group'
#     janium_account_group_id = '972fac9f-7adc-4940-86cc-95956df64ce8'
#     unassigned_account_group_id = '7c22e0c6-a778-41e5-9f22-37b06c18f34a'

#     def __init__(self, account_group_id, account_group_manager_id, dte_id, dte_sender_id, account_group_name, account_group_description):
#         self.account_group_id = account_group_id
#         self.account_group_manager_id = account_group_manager_id
#         self.dte_id = dte_id
#         self.dte_sender_id = dte_sender_id
#         self.account_group_name = account_group_name
#         self.account_group_description = account_group_description
#         # self.is_active = is_active

#     # Primary Keys
#     account_group_id = Column(String(36), primary_key=True, nullable=False)

#     # Foreign Keys
#     account_group_manager_id = Column(String(36), ForeignKey('user.user_id'), nullable=False)
#     dte_id = Column(String(36), ForeignKey('dte.dte_id'), nullable=False)
#     dte_sender_id = Column(String(36), ForeignKey('dte_sender.dte_sender_id'), nullable=False)

#     # Common Columns
#     account_group_name = Column(String(128), nullable=False)
#     account_group_description = Column(String(256), nullable=True)
#     # is_active = Column(Boolean, nullable=False, server_default=false())

#     # Table Metadata
#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

#     # SQLAlchemy Relationships and Backreferences
#     accounts = relationship('Account', backref=backref('account_group', uselist=False), lazy=False)
#     # account_group_manager = relationship('Account_group_manager', backref=backref('account_groups', uselist=True), uselist=False, lazy=True)
#     dte = relationship('Dte', backref=backref('dte_account_group'), uselist=False, lazy=True)
#     dte_sender = relationship('Dte_sender', backref=backref('dte_sender_account_group'), uselist=False, lazy=True)

# class User_account_group_map(Base):
#     __tablename__ = 'user_account_group_map'

#     def __init(self, user_id, account_group_id):
#         self.user_id = user_id
#         self.account_group_id = account_group_id
    
#     user_id = Column(String(36), ForeignKey('user.user_id'), primary_key=True, nullable=False)
#     account_group_id = Column(String(36), ForeignKey('account_group.account_group_id'), primary_key=True, nullable=False)

#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)


# class Dte_sender(Base):
#     __tablename__ = 'dte_sender'
#     janium_dte_sender_id = '5202aea8-ab36-4e6d-9cda-5994d2c0bbe1'
#     unassigned_dte_sender_id = 'd07a45e1-8baa-4593-ae54-452697e7f559'

#     def __init__(self, dte_sender_id, email_config_id, first_name, last_name):
#         self.dte_sender_id = dte_sender_id
#         self.email_config_id = email_config_id
#         self.first_name = first_name
#         self.last_name = last_name

#     # Primary Keys
#     dte_sender_id = Column(String(36), primary_key=True, nullable=False)

#     # Foreign Keys
#     user_id = Column(String(36), ForeignKey('user.user_id'), nullable=False)
#     email_config_id = Column(String(36), ForeignKey('email_config.email_config_id'), nullable=False)

#     # Table Metadata
#     date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

#     # SQLAlchemy Relationships and Backreferences
#     email_config = relationship('Email_config', uselist=False, lazy=True)


