import json
import os
import pytz
from datetime import datetime, timedelta

from sqlalchemy import (JSON, Boolean, Column, Computed, DateTime, ForeignKey,
                        Integer, PrimaryKeyConstraint, String, Table, Text,
                        create_engine, engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.sql import false, func, text, true

Base = declarative_base()


def get_session(is_remote=False, environment=None):
    if not os.getenv('LOCAL_DEV'):
        db_url = engine.url.URL(
            drivername='mysql+pymysql',
            username= os.getenv('DB_USER'),
            password= os.getenv('DB_PASSWORD'),
            database= os.getenv('DB_DATABASE'),
            host= os.getenv('DB_PRIVATE_HOST')
        )
    else:
        if is_remote:
            if environment == 'staging':
                db_url = engine.url.URL(
                    drivername='mysql+pymysql',
                    username= os.getenv('STAGING_DB_USER'),
                    password= os.getenv('STAGING_DB_PASSWORD'),
                    database= os.getenv('STAGING_DB_DATABASE'),
                    host= os.getenv('STAGING_DB_PUBLIC_HOST'),
                )
            elif environment == 'production':
                db_url = engine.url.URL(
                    drivername='mysql+pymysql',
                    username= os.getenv('PROD_DB_USER'),
                    password= os.getenv('PROD_DB_PASSWORD'),
                    database= os.getenv('PROD_DB_DATABASE'),
                    host= os.getenv('PROD_DB_PUBLIC_HOST'),
                )
        else:
            db_url = engine.url.URL(
                drivername='mysql+pymysql',
                username= os.getenv('LOCAL_DB_USER'),
                password= os.getenv('LOCAL_DB_PASSWORD'),
                database= os.getenv('LOCAL_DB_DATABASE'),
                host= os.getenv('LOCAL_DB_HOST'),
                port= os.getenv('LOCAL_DB_PORT')
            )
    sql_engine = create_engine(db_url)
    return sessionmaker(bind=sql_engine)()


class Account(Base):
    __tablename__ = 'account'
    unassigned_account_id = '8acafb6b-3ce5-45b5-af81-d357509ba457'

    def __init__(self, account_id, account_group_id, email_config_id,
                       is_sending_emails, is_sending_li_messages, is_receiving_dte,
                       effective_start_date, effective_end_date, data_enrichment_start_date,
                       data_enrichment_end_date, time_zone_id, updated_by, account_type_id):
        self.account_id = account_id
        self.account_group_id = account_group_id
        self.email_config_id = email_config_id
        self.is_sending_emails = is_sending_emails
        self.is_sending_li_messages = is_sending_li_messages
        self.is_receiving_dte = is_receiving_dte
        self.effective_start_date = effective_start_date
        self.effective_end_date = effective_end_date
        self.data_enrichment_start_date = data_enrichment_start_date
        self.data_enrichment_end_date = data_enrichment_end_date
        self.time_zone_id = time_zone_id
        self.updated_by = updated_by
        self.account_type_id = account_type_id

    account_id = Column(String(36), primary_key=True)

    account_type_id = Column(Integer, ForeignKey('account_type.account_type_id'), nullable=False)
    account_group_id = Column(String(36), ForeignKey('account_group.account_group_id'), nullable=False)
    # ulinc_config_id = Column(String(36), ForeignKey('ulinc_config.ulinc_config_id'), nullable=False)
    # email_config_id = Column(String(36), ForeignKey('email_config.email_config_id'), nullable=False)
    time_zone_id = Column(String(36), ForeignKey('time_zone.time_zone_id'), nullable=False)

    is_sending_emails = Column(Boolean, server_default=false(), nullable=False)
    is_sending_li_messages = Column(Boolean, server_default=false(), nullable=False)
    is_receiving_dte = Column(Boolean, server_default=false(), nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    data_enrichment_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    data_enrichment_end_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    # users = relationship('User_account_map', back_populates='account')
    # users = relationship('User_account_map')
    janium_campaigns = relationship('Janium_campaign', backref=backref('janium_campaign_account', uselist=False), uselist=True, lazy='dynamic')
    ulinc_campaigns = relationship('Ulinc_campaign', backref=backref('ulinc_campaign_account', uselist=False), uselist=True, lazy='dynamic')
    contacts = relationship('Contact', backref=backref('contact_account', uselist=False), uselist=True, lazy='dynamic')
    # email_config = relationship('Email_config', backref=backref('email_config_account', uselist=False), uselist=False, lazy=True)
    ulinc_configs = relationship('Ulinc_config', backref=backref('ulinc_config_account', uselist=False), uselist=True, lazy=True)
    time_zone = relationship('Time_zone', backref=backref('tz_account', uselist=True), uselist=False, lazy=True)

class Account_type(Base):
    __tablename__ = 'account_type'

    def __init__(self, account_type_id, account_type_name, account_type_description):
        self.account_type_id = account_type_id
        self.account_type_name = account_type_name
        self.account_type_description = account_type_description
    
    account_type_id = Column(Integer, primary_key=True, nullable=False)
    account_type_name = Column(String(128), nullable=False)
    account_type_description = Column(String(256), nullable=False)
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

class User(Base):
    __tablename__ = 'user'
    unassigned_user_id = '9d34bb21-7037-4709-bb0f-e1e8b1491506'
    system_user_id = 'a0bcc7a2-5e2b-41c6-9d5c-ba8ebb01c03d'

    def __init__(self, user_id, first_name, last_name, title, company, location, primary_email, campaign_management_email, alternate_dte_email, phone, updated_by):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.title = title
        self.company = company
        self.location = location
        self.primary_email = primary_email
        self.campaign_management_email = campaign_management_email
        self.alternate_dte_email = alternate_dte_email
        self.phone = phone
        self.updated_by = updated_by
    
    user_id = Column(String(36), primary_key=True)

    first_name = Column(String(126), nullable=False)
    last_name = Column(String(126), nullable=False)
    full_name = Column(String(256), Computed("CONCAT(first_name, ' ', last_name)"))
    title = Column(String(256), nullable=True)
    company = Column(String(256), nullable=True)
    location = Column(String(256), nullable=True)
    primary_email = Column(String(256), nullable=False)
    phone = Column(String(256), nullable=True)
    additional_contact_info = Column(JSON, nullable=True)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # accounts = relationship('User_account_map', back_populates='account_user')
    # permissions = relationship('User_permission_map', back_populates='permission_user')
    # accounts = relationship('User_account_map')
    # permissions = relationship('User_permission_map')


class User_account_map(Base):
    __tablename__ = 'user_account_map'

    def __init__(self, user_id, account_id, permission_id):
        self.user_id = user_id
        self.account_id = account_id
        self.permission_id = permission_id

    user_id = Column(String(36), ForeignKey('user.user_id'), primary_key=True, nullable=False)
    account_id = Column(String(36), ForeignKey('account.account_id'), primary_key=True, nullable=False)
    permission_id = Column(String(36), ForeignKey('permission.permission_id'), primary_key=True, nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # user = relationship('User', back_populates='user_accounts', foreign_keys=[user_id])
    # account = relationship('Account', back_populates='account_users', foreign_keys=[account_id])
    # user = relationship('User', foreign_keys=[user_id])
    # user = relationship('User', foreign_keys='User_account_map.user_id')
    # account = relationship('Account', foreign_keys=[account_id])


class User_proxy_map(Base):
    __tablename__ = 'user_proxy_map'

    def __init__(self, user_id, account_id):
        self.user_id = user_id
        self.account_id = account_id
    
    user_id = Column(String(36), ForeignKey('user.user_id'), primary_key=True, nullable=False)
    account_id = Column(String(36), ForeignKey('account.account_id'), primary_key=True, nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # user = relationship('User', back_populates='proxy_accounts', foreign_keys=[user_id])
    # account = relationship('Account', back_populates='proxy_users')
    # user = relationship('User', foreign_keys=[user_id])
    # account = relationship('Account', foreign_keys=[account_id])

class User_permission_map(Base):
    __tablename__ = 'user_permission_map'

    def __init__(self, user_id, permission_id):
        self.user_id = user_id
        self.permission_id = permission_id
    
    user_id = Column(String(36), ForeignKey('user.user_id'), primary_key=True, nullable=False)
    permission_id = Column(String(36), ForeignKey('permission.permission_id'), primary_key=True, nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # user = relationship('User', back_populates='permissions', foreign_keys=[user_id])
    # permission = relationship('Permission', back_populates='permission_users')
    # user = relationship('User', foreign_keys=[user_id])
    # permission = relationship('Permission', foreign_keys=[permission_id])

class Permission(Base):
    __tablename__ = 'permission'

    def __init__(self, permission_id, permission_name, permission_description):
        self.permission_id = permission_id
        self.permission_name = permission_name
        self.permission_description = permission_description
    
    permission_id = Column(String(36), primary_key=True, nullable=False)
    permission_name = Column(String(64), nullable=False)
    permission_description = Column(String(512), nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # users = relationship('User_permission_map', back_populates='permission_user')

class Permission_hierarchy(Base):
    __tablename__ = 'permission_hierarchy'

    def __init__(self, permission_hierarchy_id, parent_permission_id, child_permission_id):
        self.permission_hierarchy_id = permission_hierarchy_id
        self.parent_permission_id = parent_permission_id
        self.child_permission_id = child_permission_id
    
    permission_hierarchy_id = Column(String(36), primary_key=True, nullable=False)
    parent_permission_id = Column(String(36), ForeignKey('permission.permission_id'), nullable=False)
    child_permission_id = Column(String(36), ForeignKey('permission.permission_id'), nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # users = relationship('User_permission_map', back_populates='permission_user')

class Login_credential(Base):
    __tablename__ = 'login_credential'

    def __init__(self, login_credential_id, user_id, login_credential):
        self.login_credential_id = login_credential_id
        self.user_id = user_id
        self.login_credential = login_credential
    
    login_credential_id = Column(String(36), primary_key=True, nullable=False)
    
    user_id = Column(String(36), ForeignKey('user.user_id'), nullable=False)
    login_credential = Column(String(45), nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)



class Account_group(Base):
    __tablename__ = 'account_group'
    janium_account_group_id = '972fac9f-7adc-4940-86cc-95956df64ce8'
    unassigned_account_group_id = '7c22e0c6-a778-41e5-9f22-37b06c18f34a'

    def __init__(self, account_group_id, account_group_manager_id, dte_id, dte_sender_id, account_group_name, account_group_description):
        self.account_group_id = account_group_id
        self.account_group_manager_id = account_group_manager_id
        self.dte_id = dte_id
        self.dte_sender_id = dte_sender_id
        self.account_group_name = account_group_name
        self.account_group_description = account_group_description
        # self.is_active = is_active

    # Primary Keys
    account_group_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    account_group_manager_id = Column(String(36), ForeignKey('user.user_id'), nullable=False)
    dte_id = Column(String(36), ForeignKey('dte.dte_id'))
    dte_sender_id = Column(String(36), ForeignKey('dte_sender.dte_sender_id'), nullable=False)

    # Common Columns
    account_group_name = Column(String(128), nullable=False)
    account_group_description = Column(String(256), nullable=True)
    # is_active = Column(Boolean, nullable=False, server_default=false())

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    accounts = relationship('Account', backref=backref('account_group', uselist=False), lazy=False)
    # account_group_manager = relationship('Account_group_manager', backref=backref('account_groups', uselist=True), uselist=False, lazy=True)
    dte = relationship('Dte', uselist=False, lazy=True)
    dte_sender = relationship('Dte_sender', uselist=False, lazy=True)

class User_account_group_map(Base):
    __tablename__ = 'user_account_group_map'

    def __init(self, user_id, account_group_id):
        self.user_id = user_id
        self.account_group_id = account_group_id
    
    user_id = Column(String(36), ForeignKey('user.user_id'), primary_key=True, nullable=False)
    account_group_id = Column(String(36), ForeignKey('account_group.account_group_id'), primary_key=True, nullable=False)

    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)


class Janium_campaign(Base):
    __tablename__ = 'janium_campaign'
    unassigned_janium_campaign_id = '65c96bb2-0c32-4858-a913-ca0cd902f1fe'

    def __init__(self, janium_campaign_id, account_id, ulinc_config_id, email_config_id, janium_campaign_name, janium_campaign_description, is_messenger, is_reply_in_email_thread, queue_start_time, queue_end_time, updated_by):
        self.janium_campaign_id = janium_campaign_id
        self.account_id = account_id
        self.ulinc_config_id = ulinc_config_id
        self.email_config_id = email_config_id
        self.janium_campaign_name = janium_campaign_name
        self.janium_campaign_description = janium_campaign_description
        self.is_messenger = is_messenger
        self.is_reply_in_email_thread = is_reply_in_email_thread
        self.queue_start_time = queue_start_time
        self.queue_end_time = queue_end_time
        self.updated_by = updated_by

    # Primary Keys
    janium_campaign_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    account_id = Column(String(36), ForeignKey('account.account_id'), nullable=False)
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
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    contacts = relationship('Contact', backref=backref('contact_janium_campaign', uselist=False), uselist=True, lazy='dynamic')
    ulinc_campaigns = relationship('Ulinc_campaign', backref=backref('parent_janium_campaign', uselist=False), uselist=True, lazy='dynamic')
    janium_campaign_steps = relationship('Janium_campaign_step', backref=backref('parent_janium_campaign', uselist=False), uselist=True, lazy='dynamic')
    email_config = relationship('Email_config', backref=backref('email_config_janium_campaign', uselist=False), uselist=False, lazy=True)

    def get_effective_dates(self, timezone):
        start_date = pytz.utc.localize(self.effective_start_date).astimezone(pytz.timezone(timezone)).replace(tzinfo=None)
        end_date = pytz.utc.localize(self.effective_end_date).astimezone(pytz.timezone(timezone)).replace(tzinfo=None)
        # start_date = self.effective_start_date.astimezone(pytz.timezone(timezone)).replace(tzinfo=None)
        # end_date = self.effective_end_date.astimezone(pytz.timezone(timezone)).replace(tzinfo=None)
        return {"start": start_date, "end": end_date}
    
    def get_queue_times(self, timezone):
        start_date = pytz.utc.localize(self.queue_start_time).astimezone(pytz.timezone(timezone)).replace(tzinfo=None)
        end_date = pytz.utc.localize(self.queue_end_time).astimezone(pytz.timezone(timezone)).replace(tzinfo=None)
        return {"start": start_date, "end": end_date}

class Janium_campaign_step(Base):
    __tablename__ = 'janium_campaign_step'

    def __init__(self, janium_campaign_step_id, janium_campaign_id, janium_campaign_step_type_id,
                       janium_campaign_step_delay, janium_campaign_step_body,
                       janium_campaign_step_subject):
        self.janium_campaign_step_id = janium_campaign_step_id
        self.janium_campaign_id = janium_campaign_id
        self.janium_campaign_step_type_id = janium_campaign_step_type_id
        # self.is_active = is_active
        self.janium_campaign_step_delay = janium_campaign_step_delay
        self.janium_campaign_step_body = janium_campaign_step_body
        self.janium_campaign_step_subject = janium_campaign_step_subject

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
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    janium_campaign_step_type = relationship('Janium_campaign_step_type', uselist=False, lazy=True)


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


class Ulinc_campaign(Base):
    __tablename__ = 'ulinc_campaign'
    unassigned_ulinc_campaign_id = '943c18f3-74c8-45cf-a396-1ddc89c6b9d2'

    def __init__(self, ulinc_campaign_id, account_id, ulinc_config_id, janium_campaign_id, ulinc_campaign_name, ulinc_is_active, ulinc_ulinc_campaign_id, ulinc_is_messenger, ulinc_messenger_origin_message, updated_by):
        self.ulinc_campaign_id = ulinc_campaign_id
        self.account_id = account_id
        self.ulinc_config_id = ulinc_config_id
        self.janium_campaign_id = janium_campaign_id
        self.ulinc_campaign_name = ulinc_campaign_name
        self.ulinc_is_active = ulinc_is_active
        self.ulinc_ulinc_campaign_id = ulinc_ulinc_campaign_id
        self.ulinc_is_messenger = ulinc_is_mJessenger
        self.ulinc_messenger_origin_message = ulinc_messenger_origin_message
        self.updated_by = updated_by

    # Primary Keys
    ulinc_campaign_id = Column(String(36), primary_key=True)
    
    # Foreign Keys
    account_id = Column(String(36), ForeignKey('account.account_id'), nullable=False)
    ulinc_config_id = Column(String(36), ForeignKey('ulinc_config.ulinc_config_id'), nullable=False)
    janium_campaign_id = Column(String(36), ForeignKey('janium_campaign.janium_campaign_id'), nullable=True)

    # Common Columns
    ulinc_campaign_name = Column(String(512), nullable=False)
    ulinc_is_active = Column(Boolean, nullable=False, server_default=false())
    ulinc_ulinc_campaign_id = Column(String(16), nullable=False)
    ulinc_is_messenger = Column(Boolean, nullable=False, server_default=false())

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    contacts = relationship('Contact', backref=backref('contact_ulinc_campaign', uselist=False), lazy=False)

class Contact(Base):
    __tablename__ = 'contact'
    unassigned_contact_id = '9b84cf42-80f5-4cb4-80e6-7da4632b8177'

    def __init__(self, contact_id, contact_source_id, account_id, janium_campaign_id, ulinc_campaign_id, ulinc_id, ulinc_ulinc_campaign_id, contact_info, tib_id, updated_by):
        self.contact_id = contact_id
        self.contact_source_id = contact_source_id
        self.account_id = account_id
        self.janium_campaign_id = janium_campaign_id
        self.ulinc_campaign_id = ulinc_campaign_id
        self.ulinc_id = ulinc_id
        self.ulinc_ulinc_campaign_id = ulinc_ulinc_campaign_id
        self.contact_info = contact_info
        self.tib_id = tib_id
        self.updated_by = updated_by

    # Primary Keys
    contact_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    account_id = Column(String(36), ForeignKey('account.account_id'), nullable=False)
    janium_campaign_id = Column(String(36), ForeignKey('janium_campaign.janium_campaign_id'), nullable=False)
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
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    actions = relationship('Action', backref=backref('contact', uselist=False), uselist=True, lazy='dynamic')
    # info = relationship('Contact_info', uselist=True, lazy='dynamic')

    def get_short_ulinc_id(self, ulinc_client_id):
        return str(self.ulinc_id).replace(ulinc_client_id, '')

    def get_emails(self):
        contact_info = self.contact_info

        emails = []
        for key in contact_info:
            if key == 'ulinc':
                emails.insert(1, contact_info[key]['email'])
            elif key == 'kendo':
                if work_email := contact_info[key]['work_email']:
                    if work_email['is_valid']:
                        emails.insert(0, work_email['value'])
                    else:
                        emails.append(work_email['value'])
                if private_email := contact_info[key]['private_email']:
                    emails.append(private_email['value'])
        return emails

# class Contact_info(Base):
#     __tablename__ = 'contact_info'

#     def __init__(self, contact_info_id, contact_id, contact_info_type_id, contact_info_json):
#         self.contact_info_id = contact_info_id
#         self.contact_id = contact_id
#         self.contact_info_type_id = contact_info_type_id
#         self.contact_info_json = contact_info_json
    
#     contact_info_id = Column(String(36), primary_key=True, nullable=False)

#     contact_id = Column(String(36), ForeignKey('contact.contact_id'), nullable=False)
#     # contact_info_type_id = Column(Integer, ForeignKey('contact_info_type.contact_info_type_id'), nullable=False)

#     contact_info_json = Column(JSON, nullable=False)

#     # Table Metadata
#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

#     # SQLAlchemy Relationships and Backreferences


class Action(Base):
    __tablename__ = 'action'

    def __init__(self, action_id, contact_id, action_type_id, action_timestamp, action_message, to_email_addr=None):
        self.action_id = action_id
        self.contact_id = contact_id
        self.action_type_id = action_type_id
        self.action_timestamp = action_timestamp
        self.action_message = action_message
        self.to_email_addr = to_email_addr

    # Primary Keys
    action_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    contact_id = Column(String(36), ForeignKey('contact.contact_id'), nullable=False)
    action_type_id = Column(Integer, ForeignKey('action_type.action_type_id'), nullable=False)

    # Common Columns
    action_timestamp = Column(DateTime, nullable=True)
    action_message = Column(Text, nullable=True)
    to_email_addr = Column(String(64), nullable=True)

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences
    action_type = relationship('Action_type', uselist=False, lazy=True)


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


class Contact_source(Base):
    __tablename__ = 'contact_source'
    unassigned_contact_source_id = '950e964d-29bd-4ac6-96c4-8b27fadd8dee'

    def __init__(self, contact_source_id, account_id, contact_source_type_id, contact_source_json):
        self.contact_source_id = contact_source_id
        self.account_id = account_id
        self.contact_source_type_id = contact_source_type_id
        self.contact_source_json = contact_source_json
    
    # Primary Keys
    contact_source_id = Column(String(36), primary_key=True, nullable=False)

    # Foreign Keys
    account_id = Column(String(36), ForeignKey('account.account_id'), nullable=False)
    contact_source_type_id = Column(Integer, ForeignKey('contact_source_type.contact_source_type_id'), nullable=False)

    # Common Columns
    contact_source_json = Column(JSON, nullable=False)

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences
    contacts = relationship('Contact', backref=backref('contact_source', uselist=False), lazy=False)

class Contact_source_type(Base):
    __tablename__ = 'contact_source_type'

    def __init__(self, contact_source_type_id, contact_source_type_name, contact_source_type_description):
        self.contact_source_type_id = contact_source_type
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


# class Webhook_response(Base):
#     __tablename__ = 'webhook_response'
#     unassigned_webhook_response_id = 'b753f6f0-311a-411d-b761-3e17035bf4a6'

#     def __init__(self, webhook_response_id, client_id, webhook_response_value, webhook_response_type_id):
#         self.webhook_response_id = webhook_response_id
#         self.client_id = client_id
#         self.webhook_response_value = webhook_response_value
#         self.webhook_response_type_id = webhook_response_type_id
    
#     # Primary Keys
#     webhook_response_id = Column(String(36), primary_key=True, nullable=False)

#     # Primary Keys
#     client_id = Column(String(36), ForeignKey('client.client_id'))
#     webhook_response_type_id = Column(Integer, ForeignKey('webhook_response_type.webhook_response_type_id'))

#     # Primary Keys
#     webhook_response_value = Column(JSON, nullable=False)

#     # Table Metadata
#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     updated_by = Column(String(36), server_default=text("'45279d74-b359-49cd-bb94-d75e06ae64bc'"))

#     # SQLAlchemy Relationships and Backreferences
#     contacts = relationship('Contact', backref=backref('webhook_response', uselist=False), lazy=False)

# class Webhook_response_type(Base):
#     __tablename__ = 'webhook_response_type'

#     def __init__(self, webhook_response_type_id, webhook_response_type, webhook_response_type_description):
#         self.webhook_response_type_id = webhook_response_type_id
#         self.webhook_response_type = webhook_response_type
#         self.webhook_response_type_description = webhook_response_type_description

#     # Primary Keys
#     webhook_response_type_id = Column(Integer, primary_key=True, nullable=False)

#     # Foreign Keys

#     # Common Columns
#     webhook_response_type = Column(String(64), nullable=False)
#     webhook_response_type_description = Column(String(512), nullable=False)

#     # Table Metadata
#     asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     effective_start_date = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
#     effective_end_date = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
#     updated_by = Column(String(36), server_default=text("'45279d74-b359-49cd-bb94-d75e06ae64bc'"))

#     # SQLAlchemy Relationships and Backreferences

class Dte_sender(Base):
    __tablename__ = 'dte_sender'
    janium_dte_sender_id = '5202aea8-ab36-4e6d-9cda-5994d2c0bbe1'
    unassigned_dte_sender_id = 'd07a45e1-8baa-4593-ae54-452697e7f559'

    def __init__(self, dte_sender_id, email_config_id, first_name, last_name):
        self.dte_sender_id = dte_sender_id
        self.email_config_id = email_config_id
        self.first_name = first_name
        self.last_name = last_name

    # Primary Keys
    dte_sender_id = Column(String(36), primary_key=True)

    # Foreign Keys
    user_id = Column(String(36), ForeignKey('user.user_id'), nullable=False)
    email_config_id = Column(String(36), ForeignKey('email_config.email_config_id'), nullable=False)

    # Table Metadata
    date_added = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))

    # SQLAlchemy Relationships and Backreferences
    email_config = relationship('Email_config', uselist=False, lazy=True)


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
    dte_id = Column(String(36), primary_key=True)

    # Foreign Keys

    # Common Columns
    dte_name = Column(String(128), nullable=False)
    dte_description = Column(String(256), nullable=True)
    dte_subject = Column(String(512), nullable=False)
    dte_body = Column(Text, nullable=False)

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)
    # SQLAlchemy Relationships and Backreferences


class Email_config(Base):
    __tablename__ = 'email_config'
    janium_email_config_id = '709f79b3-7a20-43ff-844a-4f014fa4e406'
    unassigned_email_config_id = '7c5c4aa2-2c6e-4e3d-947e-6efdae4366a1'

    def __init__(self, email_config_id, credentials_id, email_server_id, is_sendgrid, sendgrid_sender_id, is_email_forward, updated_by, from_full_name, reply_to_address):
        self.email_config_id = email_config_id
        self.credentials_id = credentials_id
        self.email_server_id = email_server_id
        self.is_sendgrid = is_sendgrid
        self.sendgrid_sender_id = sendgrid_sender_id
        self.is_email_forward = is_email_forward
        self.updated_by = updated_by
        self.from_full_name = from_full_name
        self.reply_to_address = reply_to_address

    # Primary Keys
    email_config_id = Column(String(36), primary_key=True)

    # Foreign Keys
    credentials_id = Column(String(36), ForeignKey('credentials.credentials_id'))
    email_server_id = Column(String(36), ForeignKey('email_server.email_server_id'))

    # Common Columns
    from_full_name = Column(String(64), nullable=False)
    reply_to_address = Column(String(64), nullable=False)
    is_sendgrid = Column(Boolean, nullable=False, server_default=false())
    sendgrid_sender_id = Column(String(36), nullable=True)
    is_email_forward = Column(Boolean, nullable=False, server_default=false())

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    credentials = relationship('Credentials', backref=backref('email_config', uselist=False), uselist=False, lazy=True)
    email_server = relationship('Email_server', uselist=False, lazy=True)

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


class Ulinc_config(Base):
    __tablename__ = 'ulinc_config'
    unassigned_ulinc_config_id = 'dff0e400-b338-4bc5-bb99-617bade305bd'

    def __init__(self, ulinc_config_id, account_id, credentials_id, cookie_id, ulinc_client_id, new_connection_webhook, new_message_webhook, send_message_webhook, ulinc_li_email, ulinc_is_active, updated_by):
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
        self.updated_by = updated_by

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

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences
    credentials = relationship('Credentials', uselist=False)
    cookie = relationship('Cookie', uselist=False)
    account = relationship('Account', uselist=False)
    janium_campaigns = relationship('Janium_campaign', backref=backref('janium_campaign_ulinc_config', uselist=False), uselist=True)
    ulinc_campaigns = relationship('Ulinc_campaign', backref=backref('ulinc_config', uselist=False), uselist=True)


class Credentials(Base):
    __tablename__ = 'credentials'
    janium_email_app_credentials_id = 'a217fb95-0a28-49ba-a18a-a0298d0b68b3'
    unassigned_credentials_id = '264f534f-d36e-4c3c-9614-9760f47ee0e3'

    def __init__(self, credentials_id, username, password, updated_by):
        self.credentials_id = credentials_id
        self.username = username
        self.password = password
        self.updated_by = updated_by

    # Primary Keys
    credentials_id = Column(String(36), primary_key=True)

    # Foreign Keys

    # Common Columns
    username = Column(String(128), nullable=True)
    password = Column(String(128), nullable=True)

    # Table Metadata
    asOfStartTime = Column(DateTime, server_default=text("(UTC_TIMESTAMP)"))
    asOfEndTime = Column(DateTime, server_default=text("(DATE_ADD(UTC_TIMESTAMP, INTERVAL 5000 YEAR))"))
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    # SQLAlchemy Relationships and Backreferences


class Cookie(Base):
    __tablename__ = 'cookie'
    unassigned_cookie_id = 'dd0dfdaa-3d58-4d96-85dc-cd68307f528d'

    def __init__(self, cookie_id, cookie_type_id, cookie_json_value, updated_by):
        self.cookie_id = cookie_id
        self.cookie_type_id = cookie_type_id
        self.cookie_json_value = cookie_json_value
        self.updated_by = updated_by

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
    updated_by = Column(String(36), ForeignKey('user.user_id'), nullable=False)

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

    # account = relationship('Account', uselist=False, backref=backref('tz', uselist=False), lazy=True)
