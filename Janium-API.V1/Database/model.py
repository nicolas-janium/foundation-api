from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime,ForeignKey, Date
import json
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import sys
sys.path.append("../")
from Database.db_vars import DatabaseVars as dbvar

app = Flask(__name__)
db = SQLAlchemy(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://api:api@localhost:3307/janium"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


class Email_Server(db.Model):
    __tablename__ = 'email_server'
    email_server_id = Column(String, primary_key=True)
    email_server_name = Column(String)
    smtp_address = Column(String)
    smtp_tls_port = Column(Integer)
    smtp_ssl_port = Column(Integer)
    imap_address = Column(String)
    imap_ssl_port = Column(Integer)
    date_added = Column(DateTime)

    def initial_population():
        qry = Email_Server.query.filter(Email_Server.email_server_id == dbvar.api_user_id).all()
        if len(qry) == 0:
            load = Email_Server(
                email_server_id = dbvar.email_server_id,
                email_server_name = 'Initial Server Name',
                smtp_address = 'Smtp Address',
                smtp_tls_port = 0,
                smtp_ssl_port = 0,
                imap_address = 'IMAP Address',
                imap_ssl_port = 0,
                date_added = dbvar.dt_format
            )
            db.session.add(load)
            db.session.commit()

class User(db.Model):
    __tablename__ = 'user'
    user_id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    title = Column(String, nullable=True)    
    company = Column(String, nullable=True)
    location = Column(String, nullable=True)
    primary_email = Column(String)
    phone = Column(String, nullable=True)
    additional_contact = Column(JSON, nullable=True)
    asOfStartTime = Column(DateTime, nullable=True)
    asOfEndTime = Column(DateTime, nullable=True)
    updated_by = Column(String)

    def initial_population():
        # Add the API User
        qry = User.query.filter(User.user_id == dbvar.api_user_id).all()
        if len(qry) == 0:
            usr = User(user_id=dbvar.api_user_id
                    ,asOfStartTime=dbvar.dt_format
                    ,asOfEndTime='9999-12-31 10:10:10'
                    ,primary_email='api@janium.io')
            db.session.add(usr)
            db.session.commit()
        # Add Jason's User
        qry = User.query.filter(User.user_id == dbvar.jason_user_id).all()
        if len(qry) == 0:
            usr = User(user_id=dbvar.jason_user_id
                        , first_name='Jason'
                        , last_name='Hawkes'
                        , title='Partner'
                        , company='Janium'
                        , location='Parker, Colorado'
                        , primary_email='jason@janium.io'
                        , phone='2083461732'
                        , asOfStartTime=dbvar.dt_format
                        , asOfEndTime='9999-12-31 10:10:10'
                        , updated_by=dbvar.api_user_id)
            db.session.add(usr)
            db.session.commit()


class LoginCredential(db.Model):
    __tablename__ = 'login_credential'
    def __init__(self, credential_id, user_id, credential, asOfStartTime, asOfEndTime, updated_by):
        self.credential_id = credential_id
        self.user_id = user_id
        self.credential = credential
        self.asOfStartTime = asOfStartTime
        self.asOfEndTime = asOfEndTime
        self.updated_by = updated_by
    
    credential_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("user.user_id"))
    credential = Column(String)
    asOfStartTime = Column(DateTime)
    asOfEndTime = Column(DateTime)
    updated_by = Column(String)
    user_relationship = relationship("User", primaryjoin=user_id == User.user_id)

    def initial_population():
        qry = LoginCredential.query.filter(LoginCredential.user_id == dbvar.api_user_id).all()
        if len(qry) == 0:
            cred_id = 'd4ca0c20-83b7-11eb-bed9-0242ac110002'    
            user_cred = LoginCredential(credential_id=cred_id
                                        , user_id=dbvar.api_user_id
                                        , credential='superSafePa$$'
                                        , asOfStartTime=dbvar.dt_format
                                        , asOfEndTime='9999-12-31 10:10:10'
                                        , updated_by=dbvar.api_user_id)
            db.session.add(user_cred)
            db.session.commit()
        
        qry = LoginCredential.query.filter(LoginCredential.user_id == dbvar.jason_user_id).all()
        if len(qry) == 0:
            cred_id = 'd4ca0c20-83b7-11eb-bed9-0242ac110003'    
            user_cred = LoginCredential(credential_id=cred_id
                                        , user_id=dbvar.jason_user_id
                                        , credential='superSafePa$$'
                                        , asOfStartTime=dbvar.dt_format
                                        , asOfEndTime='9999-12-31 10:10:10'
                                        , updated_by=dbvar.api_user_id)
            db.session.add(user_cred)
            db.session.commit()

class User_Account_Map(db.Model):
    __tablename__ = 'user_account_map'
    user_id = Column(String(36), ForeignKey('user.user_id'), primary_key=True)
    account_id = Column(String(36), ForeignKey('account.account_id'), primary_key=True)
    asOfStartTime = Column(DateTime)
    asOfEndTime = Column(DateTime)
    updated_by = Column(String(36))

class Account_Type(db.Model):
    __tablename__ = 'account_type'
    account_type_id = Column(Integer, primary_key=True)
    account_type_name = Column(String)
    account_type_description = Column(String)
    date_added = Column(DateTime)

    def initial_population():
        qry = Account_Type.query.filter(Account_Type.account_type_id == 1).all()
        if len(qry) == 0:
            account_type = Account_Type(
                account_type_id = 1,
                account_type_name = 'Account Type',
                account_type_description = 'Account Type Description',
                date_added = dbvar.dt_format)
            db.session.add(account_type)
            db.session.commit()

class Account_Group(db.Model):
    __tablename__ = 'account_group'
    account_group_id = Column(String, primary_key=True)
    account_group_manager_id = Column(String)
    dte_id = Column(String)
    dte_sender_id = Column(String)
    account_group_name = Column(String)
    account_group_description = Column(String)
    asOfStartTime = Column(DateTime)
    asOfEndTime = Column(DateTime)
    effective_start_date = Column(Date)
    effective_end_date = Column(Date)
    updated_by = Column(String)

    def initial_population():
        qry = Account_Group.query.filter(Account_Group.account_group_id == 0).all()
        if len(qry) == 0:
            pop = Account_Group(
                account_group_id = Column(String, primary_key=True)
                account_group_manager_id = Column(String)
                dte_id = Column(String)
                dte_sender_id = Column(String)
                account_group_name = 'Account Group Name'
                account_group_description = 'Account Group Description'
                asOfStartTime = dbvar.dt_format
                asOfEndTime = '9999-12-31 10:10:10'
                effective_start_date = dbvar.date
                effective_end_date = '9999-12-31'
                updated_by = dbvar.api_user_id)
            db.session.add(pop)
            db.session.commit()


class Account(db.Model):
    __tablename__ = 'account'
    account_id = Column(String, primary_key=True)
    account_type_id = Column(Integer, ForeignKey('account_type.account_type_id'))
    account_group_id = Column(String)
    ulinc_config_id = Column(String)
    email_config_id = Column(String)
    time_zone_id = Column(String)
    is_sending_emails = Column(Integer)
    is_sending_li_messages = Column(Integer)
    is_receiving_dte = Column(Integer)
    asOfStartTime = Column(DateTime)
    asOfEndTime = Column(DateTime)
    effective_start_date = Column(Date)
    effective_end_date = Column(Date)
    data_enrichment_start_date = Column(Date)
    data_enrichment_end_date = Column(Date)
    updated_by = Column(String)

    def initial_population():
        qry = Account.query.filter(Account.account_id == dbvar.jason_account_id).all()
        if len(qry) == 0:
            account = Account(account_id=dbvar.jason_account_id
                        , account_type_id=1
                        , account_group_id=0
                        , ulinc_config_id='ulinc_config_id'
                        , email_config_id='email_config_id'
                        , time_zone_id='time_zone_id'
                        , is_sending_emails=1
                        , is_sending_li_messages=1
                        , is_receiving_dte=1
                        , asOfStartTime=dbvar.dt_format
                        , asOfEndTime='9999-12-31 10:10:10'
                        , effective_start_date=dbvar.date
                        , effective_end_date='9999-12-31'
                        , data_enrichment_start_date=dbvar.date
                        , data_enrichment_end_date=dbvar.date
                        , updated_by=dbvar.api_user_id)
            db.session.add(account)
            db.session.commit()