from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float
import os
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from flask_mail import Mail, Message
from db_model import Client, Campaign, Action, Email_server, Session
import mysql.connector
import random
import uuid
import string
import jwt as jwt_1
from datetime import timedelta
import base

app = Flask(__name__)
db=SQLAlchemy(app)
jwt = JWTManager(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://brandon:brandon123@34.123.188.250/janium_master"
jwt_access_key = 'super-secret'
app.config['JWT_SECRET_KEY'] = jwt_access_key 
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=10)
jwt_algos = ["HS256"]
db_user = 'brandon'
db_password = 'brandon123'
db_name = 'janium_master'
db_connection_name = 'janium0-0:us-central1:janium-master'
unix_socket = '/cloudsql/{}'.format(db_connection_name)

"""
We need to create a very non-privileged user that only has select, insert and update privileges on the database to perform all of these actions
We also need to be able to split these routes out into different files. https://flask.palletsprojects.com/en/1.1.x/patterns/packages/
"""


def conn():
    db = mysql.connector.connect(username=db_user
    , password=db_password
    , database=db_name
    #, unix_socket=unix_socket
    , host='34.123.188.250'
    )
    return db


def create_password(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

def jwt_token(input):
    token=input
    jwt_data=jwt_1.decode(token[7:], jwt_access_key, algorithms=["HS256"])
    return jwt_data

@app.route('/')
def hello_world():

    db = conn()

    cursor = db.cursor()
    cursor.execute("select id from client;")

    client_id = []
    for i in cursor:
        client_id.append(i)
        print(i)
    cursor.close()
    db.close()

    return jsonify(client_id) #client


# Start with the login
@app.route('/login', methods=['POST'])
def login():
    """
    Need Logic to work on brute force attacks with the ability to lock out users after a number of bad attempts.
    Also need to see where users are logging in from.
    Need to add hashing to the passwords so that we don't store them in clear text.
    Need to add proxy authentication so that we can impersonate a user and check what is going on with their account for debugging.
    """
    if request.is_json:
        email = request.json['email']
        password = request.json['password']
    else:
        email = request.form['email']
        password = request.form['password']

    db = conn()
    #email='jason@janium.io'
    #password='superSafePa$$'

    login_query = "select \
                      u.user_id user_id\
                    , u.username \
                    , crd.credential \
                    from \
                    users_vw u \
                    join \
                    credentials crd \
                        on u.user_id = crd.client_id \
                    where u.username  = '{}' \
                      and crd.credential = '{}';".format(email,password)

    print(login_query)
    cursor=db.cursor()
    cursor.execute(login_query)
    
    #client_id=cursor[3]
    for i in cursor:
        user_id = i[0]
        print(i[0])

    

    # If something doesn't work it means that there is a bad username or password
    if 'user_id' not in locals():
        login_flag=False
    else:
        login_flag=True  

    if login_flag:
        client_query = "select distinct client_id, email from user_account_map um join client c on um.client_id = c.id where user_id = '{}';".format(user_id)
        cursor.execute(client_query)
        clients = []
        for i in cursor:
            clients.append({"client_id":i[0], "client_email": i[1]})

        cursor.close()
        db.close()

        additional_data={"uid": user_id}

        access_token = create_access_token(identity=email, additional_claims=additional_data)
        return jsonify(message="Login succeeded!", access_token=access_token, clients=clients)
    else:
        cursor.close()
        db.close()
        return jsonify(message="Bad email or password"), 401
    return jsonify(client_id=client_id)


@app.route('/api/v1/create_user', methods=['POST'])
@jwt_required()
def create_user():
    email = request.args.get('email') or "<null>"
    accountEmail = request.args.get('accountEmail') or "<null>"
    ulincid = request.args.get('ulincid') or "<null>"
    ulinc_username = request.args.get('ulinc_username') or "<null>"
    ulinc_password = request.args.get('ulinc_password') or "<null>"
    print(email)

    # Check if user has privileges to create user.
    jwt_token=request.headers.get('authorization')
    jwt_data=jwt_1.decode(jwt_token[7:], jwt_access_key, algorithms=jwt_algos)

    db = conn()
    cursor=db.cursor()
    check_privs="select count(*) from users_vw c join privileges p on c.user_id = p.client_id join privilege_type pt on p.privilege_type_id = pt.privilege_type_id where c.username='{}' and c.user_id = '{}' and pt.privilege_type='Create User';".format(jwt_data['sub'], jwt_data['uid'])
    print(check_privs)
    cursor.execute(check_privs)

    for i in cursor:
        priv_cnt=int(i[0])

    if priv_cnt == 0:
        # need to add lots of logging to detect unauthorized attempts.
        return jsonify(message="User does not have the create user privilege!")


    # Check if the email already exists
    user_exits="select count(*) from users_vw where username = '{}';".format(email)
    print(user_exits)
    
    cursor.execute(user_exits)
    for i in cursor:
        cnt=int(i[0])

    new_id=uuid.uuid1()
    print(new_id)
    print(cnt, type(cnt))
    if cnt > 0:
        cursor.close()
        db.close()
        return jsonify(message="User with email of: {} already exists".format(email))
    else:
        password=create_password(25)
        if email == accountEmail or email == "<null>":
            if ulincid == "<null>":
                return jsonify(message="Ulinc Email Required"), 401
            create_user="insert into client (id, dateadded, email, ulincid, ulinc_username, ulinc_password, is_dte) values ('{}', now(), '{}','{}','{}','{}', 0);".format(new_id, accountEmail, ulincid, ulinc_username, ulinc_password)
        else:
            create_user="insert into users (user_id, username, last_updated_by, last_updated_date, created_by, created_date) values ('{}','{}','{}',now(),'{}',now());".format(new_id, email,jwt_data['uid'],jwt_data['uid'])
        
        cursor.execute(create_user)
        create_credential="insert into credentials(client_id, credential) values('{}', '{}');".format(new_id, password)
        cursor.execute(create_credential)
        db.commit()
        cursor.close()
        db.close()
        # Add piece to sync Ulinc campaigns
        # Add piece to send email to user to update their profile
        return jsonify(message="A user for the email: {} has been created.".format(email))


@app.route('/api/v1/get_user', methods=['GET'])
@jwt_required()
def get_user():
    jwt_data=jwt_token(request.headers.get('authorization'))
    db = conn()
    cursor=db.cursor()
    get_user_query="select user_id, username, first_name, last_name, title, company from users_vw where user_id = '{}' order by user_id limit 1;".format(jwt_data['uid'])
    cursor.execute(get_user_query)
    for i in cursor:
        user={
              "user_id":i[0]
            , "username":i[1]
            , "first_name":i[2]
            , "last_name":i[3]
            , "title":i[4]
            , "company":i[5]
        }
    get_accounts_query="select distinct client_id, c.email, coalesce(c.firstname, '<NULL>') firstname, coalesce(c.lastname, '<NULL>') lastname from user_account_map um join client c on um.client_id = c.id where user_id = '{}';".format(jwt_data['uid'])
    cursor.execute(get_accounts_query)
    accounts = []
    for i in cursor:
        accounts.append({"account_id":i[0], "email":i[1], "full_name":i[2]+' '+i[3]})

    rolling_stats=[]
    for i in accounts:
        agg_statement=" select 'New Connections' as action_type, \
                            count(distinct case when a.action_code = 1 and datediff(now(), a.dateadded) < 2 then co.id end) as 24h, \
                            count(distinct case when a.action_code = 1 and datediff(now(), a.dateadded) < 4 then co.id end) as 72h, \
                            count(distinct case when a.action_code = 1 and datediff(now(), a.dateadded) < 8 then co.id end) as week, \
                            count(distinct case when a.action_code = 1 and datediff(now(), a.dateadded) < 32 then co.id end) as month, \
                            count(distinct case when a.action_code = 1 then co.id end) as total \
                        from client cl \
                        inner join contact co on co.clientid = cl.id \
                        inner join activity a on a.contactid = co.id \
                        where cl.id = '{client_id}' \
                        UNION \
                        select 'LI Responses' as action_type, \
                            count(distinct case when a.action_code = 2 and datediff(now(), a.action_timestamp) < 2 then co.id end) as 24h, \
                            count(distinct case when a.action_code = 2 and datediff(now(), a.action_timestamp) < 4 then co.id end) as 72h, \
                            count(distinct case when a.action_code = 2 and datediff(now(), a.action_timestamp) < 8 then co.id end) as week, \
                            count(distinct case when a.action_code = 2 and datediff(now(), a.action_timestamp) < 32 then co.id end) as month, \
                            count(distinct case when a.action_code = 2 then co.id end) as total \
                        from client cl \
                        inner join contact co on co.clientid = cl.id \
                        inner join activity a on a.contactid = co.id \
                        where cl.id = '{client_id}' \
                        UNION \
                        select 'LI Messages Sent' as action_type, \
                            count(distinct case when a.action_code = 3 and datediff(now(), a.action_timestamp) < 2 then co.id end) as 24h, \
                            count(distinct case when a.action_code = 3 and datediff(now(), a.action_timestamp) < 4 then co.id end) as 72h, \
                            count(distinct case when a.action_code = 3 and datediff(now(), a.action_timestamp) < 8 then co.id end) as week, \
                            count(distinct case when a.action_code = 3 and datediff(now(), a.action_timestamp) < 32 then co.id end) as month, \
                            count(distinct case when a.action_code = 3 then co.id end) as total \
                        from client cl \
                        inner join contact co on co.clientid = cl.id \
                        inner join activity a on a.contactid = co.id \
                        where cl.id = '{client_id}' \
                        UNION \
                        select 'Email Responses' as action_type, \
                            count(distinct case when a.action_code = 6 and datediff(now(), a.action_timestamp) < 2 then co.id end) as 24h, \
                            count(distinct case when a.action_code = 6 and datediff(now(), a.action_timestamp) < 4 then co.id end) as 72h, \
                            count(distinct case when a.action_code = 6 and datediff(now(), a.action_timestamp) < 8 then co.id end) as week, \
                            count(distinct case when a.action_code = 6 and datediff(now(), a.action_timestamp) < 32 then co.id end) as month, \
                            count(distinct case when a.action_code = 6 then co.id end) as total \
                        from client cl \
                        inner join contact co on co.clientid = cl.id \
                        inner join activity a on a.contactid = co.id \
                        where cl.id = '{client_id}' \
                        UNION \
                        select 'Emails Sent' as action_type, \
                            count(distinct case when a.action_code = 4 and datediff(now(), a.action_timestamp) < 2 then co.id end) as 24h, \
                            count(distinct case when a.action_code = 4 and datediff(now(), a.action_timestamp) < 4 then co.id end) as 72h, \
                            count(distinct case when a.action_code = 4 and datediff(now(), a.action_timestamp) < 8 then co.id end) as week, \
                            count(distinct case when a.action_code = 4 and datediff(now(), a.action_timestamp) < 32 then co.id end) as month, \
                            count(distinct case when a.action_code = 4 then co.id end) as total \
                        from client cl \
                        inner join contact co on co.clientid = cl.id \
                        inner join activity a on a.contactid = co.id \
                        where cl.id = '{client_id}';".format(client_id=i['account_id'])
        cursor.execute(agg_statement)
        client_stats=[]
        for j in cursor:
            client_stats.append({"stat_type":j[0], "1d": j[1], "3d": j[2], "7d": j[3], "30d": j[4], "Total": j[5]})
        stats_dict={}
        stats_dict[i['account_id']]=client_stats
        rolling_stats.append(stats_dict)
    
    for i in rolling_stats:
        for j in i:
            cntr=0
            for k in accounts:
                if j == k['account_id']:
                    accounts[cntr].update(rolling_stats=i[j])
                cntr+=1

    for i in accounts:
        client_stats_query="select cl.id as clientid, \
                            coalesce(cl.ulinc_tasks_in_queue, 0) ulinc_tasks_in_queue, \
                            count(distinct case when ca.id is not null and ca.isactive = 1 then ca.id end) as active_janium_campaigns, \
                            count(distinct case when uc.janium_campaignid is not null then uc.id end) as assoc_ulinc_campaign, \
                            count(distinct case when ca.id is not null and ca.is_messenger <> 1 then ca.id end) as janium_connector_campaigns, \
                            count(distinct case when ca.id is not null and ca.is_messenger = 1 then ca.id end) as janium_messenger_campaigns, \
                            count(distinct case when uc.id is not null and uc.ulinc_is_messenger <> 1 then uc.id end) as ulinc_connector_campaigns, \
                            count(distinct case when uc.id is not null and uc.ulinc_is_messenger = 1 then uc.id end) as ulinc_messenger_campaigns, \
                            date(min(co.dateadded)) as first_data, \
                            cl.isactive \
                        from client cl \
                        left join campaign ca on ca.clientid = cl.id \
                        left join ulinc_campaign uc on uc.clientid = cl.id \
                        left join contact co on co.clientid = cl.id \
                        where cl.id = '{}' \
                        group by cl.id, cl.firstname, cl.lastname".format(i['account_id'])
        cursor.execute(client_stats_query)
    
        for j in cursor:
            client_stats={"ulinc_tasks_in_queue":j[1], "active_janium_campaigns":j[2], "assoc_ulinc_campaign":j[3], "janium_connector_campaigns":j[4], "janium_messenger_campaigns":j[5], "ulinc_connector_campaigns":j[6], "ulinc_messenger_campaigns":j[7]}
            cntr=0
            for k in accounts:
                if j[0] == k['account_id']:
                    accounts[cntr].update(stats=client_stats)
                cntr+=1

    cursor.close() 
    db.close()

    return jsonify(user=user, accounts=accounts)


@app.route('/api/v1/update_user', methods=['PUT'])
@jwt_required()
def update_user():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    company  = request.form['company']
    title = request.form['title']
        
    print(first_name, last_name, title, company)
    jwt_data=jwt_token(request.headers.get('authorization'))
    db = conn()
    cursor=db.cursor()
    cursor.execute("select count(*) from client where id = '{}';".format(jwt_data['uid']))
    for i in cursor:
        cnt=i[0]
    if cnt == 0:
        update_user_query = "update users set first_name = '{}', last_name = '{}', title = '{}', company = '{}' where user_id = '{}';".format(first_name, last_name, company, title, jwt_data['uid'])
    else:
        update_user_query = "update client set firstname = '{}', lastname = '{}', title = '{}', company = '{}' where id = '{}';".format(first_name, last_name, title, company, jwt_data['uid'])
    print(update_user_query)
    cursor.execute(update_user_query)
    db.commit()
    cursor.close()
    db.close()

    return jsonify(message="User Sucessfully Updated")


# Add a user to be able to access a Janium Account
@app.route('/api/v1/add_user_to_account')


@app.route('/api/v1/get_account/<string:account_id>', methods=['GET'])
@jwt_required()
def get_account(account_id:str):
    # This will return all information on the user
    jwt_data=jwt_token(request.headers.get('authorization'))
    
    db = conn()
    cursor=db.cursor()

    chk_permissions = "select count(*) from user_account_map where user_id = '{}' and client_id = '{}';".format(jwt_data['uid'], account_id)
    cursor.execute(chk_permissions)
    for i in cursor:
        chk_cnt = i[0]

    if chk_cnt == 0:
        return jsonify(message="User does not have permissions to view this account."), 402

    args = [account_id]
    cursor.callproc('new_connections', args)
    for i in cursor.stored_results():
        new_conn_res = i.fetchall()

    cursor.callproc('new_messages', args)
    for i in cursor.stored_results():
        new_mess_res = i.fetchall()

    cursor.callproc('vm_tasks', args)
    for i in cursor.stored_results():
        vm_tasks_res = i.fetchall()

    get_account_query="select ulincid, ulinc_username, ulinc_password, email_app_username, email_app_password, new_connection_wh, new_message_wh, send_message_wh \
    , is_sending_li_messages, is_sending_emails, is_sendgrid, sendgrid_sender_id, clientmanager, dte_sender_id, daily_tasks_email_id, email_server_id from client where id = '{}'".format(account_id)

    print(get_account_query)
    cursor.execute(get_account_query)

    for i in cursor:
        ret = {
              "ulincid": i[0]
            , "ulinc_username": i[1]
            , "ulinc_password": i[2]
            , "email_app_username": i[3]
            , "email_app_password": i[4]
            , "new_connection_wh": i[5]
            , "new_message_wh": i[6]
            , "send_message_wh": i[7]
            , "is_sending_li_messages": i[8]
            , "is_sending_emails": i[9]
            , "is_sendgrid": i[10]
            , "sendgrid_sender_id": i[11]
            , "clientmanager": i[12]
            , "dte_sender_id": i[13]
            , "daily_tasks_email_id": i[14]
            , "email_server_id": i[15]
        }

    get_campaigns="select ca.id as campaignid, \
                ca.name as 'Campaign Name', \
                ca.description, \
                ca.isactive \
                from campaign ca \
                inner join client cl on cl.id = ca.clientid \
                where cl.id = '{}'".format(account_id)

    cursor.execute(get_campaigns)

    campaigns_arr = []
    for i in cursor:
        campaigns_arr.append({
              "campaign_id": i[0]
            , "campaign_name": i[1] 
            , "description": i[2]
            , "isactive": i[3]
        })

    cursor.close()
    db.close()

    new_conn_arr = []
    for i in new_conn_res:
        new_conn_arr.append({
              "contactFullName":i[0]
            , "title": i[2]
            , "company": i[3]
            , "location": i[4]
            , "campaignName": i[5]
            , "dateAdded": i[6]
            , "li_profile_url": i[7]
            , "contactId": i[8]
        })

    new_mess_arr = []
    for i in new_mess_res:
        new_mess_arr.append({
              "contactFullName": i[0]
            , "title": i[2]
            , "company": i[3]
            , "location": i[4]
            , "campaignName": i[5]
            , "source": i[6]
            , "action_dateadded": i[7]
            , "li_profile_URL": i[8]
            , "contact_id": i[9]
            , "max_act_id": i[10]
        })

    vm_tasks_arr = []
    for i in vm_tasks_res:
        vm_tasks_arr.append({
              "contact_fullname": i[0]
            , "title": i[2]
            , "company": i[3]
            , "location": i[4]
            , "phone": i[5]
            , "campaignName": i[6]
            , "contact_id": i[7]
            , "li_profile_URL": i[[8]]
        })

    

    ret['new_connections'] = new_conn_arr
    ret['new_messages'] = new_mess_arr
    ret['vm_tasks'] = vm_tasks_arr 
    ret['campaigns'] = campaigns_arr

    return jsonify(ret)


@app.route('/api/v1/update_account/<string:account_id>', methods=['PUT'])
@jwt_required()
def update_account(account_id: str):
    ulincid = request.form['ulincid']
    ulinc_username = request.form['ulinc_username']
    ulinc_password = request.form['ulinc_password']
    email_app_username = request.form['email_app_username']
    email_app_password = request.form['email_app_password']
    new_connection_wh = request.form['new_connection_wh']
    new_message_wh = request.form['new_message_wh']
    send_message_wh = request.form['send_message_wh']
    is_sending_li_messages = request.form['is_sending_li_messages']
    is_sending_emails = request.form['is_sending_emails']
    is_sendgrid = request.form['is_sendgrid']
    sendgrid_sender_id = request.form['sendgrid_sender_id']
    clientmanager = request.form['clientmanager']
    dte_sender_id = request.form['dte_sender_id']
    daily_tasks_email_id = request.form['daily_tasks_email_id']
    email_server_id = request.form['email_server_id']

    jwt_data=jwt_token(request.headers.get('authorization'))
    
    db = conn()
    cursor=db.cursor()

    chk_permissions = "select count(*) from user_account_map where user_id = '{}' and client_id = '{}';".format(jwt_data['uid'], account_id)
    cursor.execute(chk_permissions)
    for i in cursor:
        chk_cnt = i[0]

    if chk_cnt == 0:
        cursor.close()
        db.close()
        return jsonify(message="User does not have permissions to update this account."), 402

    update_account_qry = "update client set \
          ulincid = '{ulincid}' \
        , ulinc_username = '{ulinc_username}' \
        , ulinc_password = '{ulinc_password}' \
        , email_app_username = '{email_app_username}' \
        , email_app_password = '{email_app_password}' \
        , new_connection_wh = '{new_connection_wh}' \
        , new_message_wh = '{new_message_wh}' \
        , send_message_wh = '{send_message_wh}' \
        , is_sending_li_messages = '{is_sending_li_messages}' \
        , is_sending_emails = '{is_sending_emails}' \
        , is_sendgrid = '{is_sendgrid}' \
        , sendgrid_sender_id = '{sendgrid_sender_id}' \
        , clientmanager = '{clientmanager}' \
        , dte_sender_id = '{dte_sender_id}' \
        , daily_tasks_email_id = '{daily_tasks_email_id}' \
        , email_server_id  = '{email_server_id}' \
        where id = '{account_id}';".format(
              ulincid=ulincid
            , ulinc_username=ulinc_username
            , ulinc_password=ulinc_password
            , email_app_username=email_app_username
            , email_app_password=email_app_password
            , new_connection_wh=new_connection_wh
            , new_message_wh=new_message_wh
            , send_message_wh=send_message_wh
            , is_sending_li_messages=is_sending_li_messages
            , is_sending_emails=is_sending_emails
            , is_sendgrid=is_sendgrid
            , sendgrid_sender_id=sendgrid_sender_id
            , clientmanager=clientmanager
            , dte_sender_id=dte_sender_id
            , daily_tasks_email_id=daily_tasks_email_id
            , email_server_id=email_server_id
            , account_id=account_id
        )

    print(update_account_qry)

    cursor.execute(update_account_qry)
    db.commit()
    cursor.close()
    db.close()

    return jsonify(message="Account sucessfully updated!")


@app.route('/api/v1/get_campaign/<string:account_id>/<string:campaign_id>', methods=['GET'])
@jwt_required()
def get_campaign(account_id:str, campaign_id:str):
    jwt_data=jwt_token(request.headers.get('authorization'))
    db = conn()
    cursor=db.cursor()

    chk_permissions = "select count(*) from user_account_map where user_id = '{}' and client_id = '{}';".format(jwt_data['uid'], account_id)
    cursor.execute(chk_permissions)
    for i in cursor:
        chk_cnt = i[0]

    if chk_cnt == 0:
        cursor.close()
        db.close()
        return jsonify(message="User does not have permissions to update campaigns for this Account."), 402

    get_campaign_qry = "select \
                        ca.id as campaignid, \
                        'after_campaign' as template_name, \
                        ca.send_email_after_c send_email_after, \
                        ca.automate_email_after_c as automate_after_email, \
                        ca.email_after_c_sendgrid_template_id as sendgrid_template_id, \
                        ca.email_after_c_subject as template_subject,  \
                        ca.email_after_c_body as template_body, \
                        ca.email_after_c_delay as template_delay \
                        from campaign ca \
                        inner join client cl on cl.id = ca.clientid \
                        where cl.id = '{account_id}' \
                        and ca.id = '{campaign_id}'  \
                        union \
                        select  \
                        ca.id as campaignid, \
                        'after_welcome_message' as template_name, \
                        ca.send_email_after_wm, \
                        ca.automate_email_after_wm, \
                        ca.email_after_wm_sendgrid_template_id, \
                        ca.email_after_wm_subject, \
                        ca.email_after_wm_body, \
                        ca.email_after_wm_delay \
                        from campaign ca \
                        inner join client cl on cl.id = ca.clientid \
                        where cl.id = '{account_id}' \
                        and ca.id = '{campaign_id}'  \
                        union \
                        select  \
                        ca.id as campaignid, \
                        'followup_1_email' as template_name, \
                        ca.send_followup1_email, \
                        ca.automate_followup1_email, \
                        ca.followup1_email_sendgrid_template_id, \
                        ca.followup1_email_subject, \
                        ca.followup1_email_body, \
                        ca.followup1_email_delay \
                        from campaign ca \
                        inner join client cl on cl.id = ca.clientid \
                        where cl.id = '{account_id}' \
                        and ca.id = '{campaign_id}'  \
                        union \
                        select  \
                        ca.id as campaignid, \
                        'followup_2_email' as template_name, \
                        ca.send_followup2_email, \
                        ca.automate_followup2_email, \
                        ca.followup2_email_sendgrid_template_id, \
                        ca.followup2_email_subject, \
                        ca.followup2_email_body, \
                        ca.followup2_email_delay \
                        from campaign ca \
                        inner join client cl on cl.id = ca.clientid \
                        where cl.id = '{account_id}' \
                        and ca.id = '{campaign_id}'  \
                        union \
                        select  \
                        ca.id as campaignid, \
                        'followup_3_email' as template_name, \
                        ca.send_followup3_email, \
                        ca.automate_followup3_email, \
                        ca.followup3_email_sendgrid_template_id, \
                        ca.followup3_email_subject, \
                        ca.followup3_email_body, \
                        ca.followup3_email_delay \
                        from campaign ca \
                        inner join client cl on cl.id = ca.clientid \
                        where cl.id = '{account_id}' \
                        and ca.id = '{campaign_id}';".format(account_id=account_id, campaign_id=campaign_id)
    cursor.execute(get_campaign_qry)
    campaign_arr=[]
    for i in cursor:
        campaign_arr.append({
              "template_name": i[1]
            , "send_email_after": i[2]
            , "automate_after_email": i[3]
            , "sendgrid_template_id": i[4]
            , "template_subject": i[5]
            , "template_body": i[6]
            , "template_delay": i[7]
        })
    get_campaigns="select ca.name as 'Campaign Name', \
                ca.description, \
                ca.isactive \
                from campaign ca \
                inner join client cl on cl.id = ca.clientid \
                where cl.id = '{}' \
                  and ca.id = '{}';".format(account_id,campaign_id)

    cursor.execute(get_campaigns)
    for i in cursor:
        campaign_name=i[0]
        description=i[1]
        isactive=i[2]

    cursor.close()
    db.close()

    return jsonify(campaign_id=campaign_id, campaign_info=campaign_arr, campaign_name=campaign_name, description=description, isactive=isactive)


@app.route('/api/v1/create_campaign/<string:account_id>', methods=['POST'])
@jwt_required()
def create_campaign(account_id:str):
    jwt_data=jwt_token(request.headers.get('authorization'))
    db = conn()
    cursor=db.cursor()

    chk_permissions = "select count(*) from user_account_map where user_id = '{}' and client_id = '{}';".format(jwt_data['uid'], account_id)
    cursor.execute(chk_permissions)
    for i in cursor:
        chk_cnt = i[0]

    if chk_cnt == 0:
        cursor.close()
        db.close()
        return jsonify(message="User does not have permissions to create campaigns for this Account."), 402

    campaign=request.json
    
    campaign_name=campaign['campaign_name']

    check_campaign_qry="select count(*) from client c join campaign ca on c.id = ca.clientid where c.id = '{}' and ca.name = '{}';".format(account_id, campaign_name)
    print(check_campaign_qry)
    cursor.execute(check_campaign_qry)
    for i in cursor:
        cmpgn_chk=i[0]

    if cmpgn_chk > 0:
        cursor.close()
        db.close()
        return jsonify(message="Campaign by that name already exists.")

    new_id=uuid.uuid1()
    for i in campaign['campaign_info']:
        if i['template_name'] == 'after_campaign':
            send_email_after_c=i['send_email_after']
            automate_email_after_c=i['automate_after_email']
            email_after_c_sendgrid_template_id=i['sendgrid_template_id']
            email_after_c_subject=i['template_subject']
            email_after_c_body=i['template_body']
            email_after_c_delay=i['template_delay']
        if i['template_name'] == 'after_welcome_message':
            send_email_after_wm=i['send_email_after']
            automate_email_after_wm=i['automate_after_email']
            email_after_wm_sendgrid_template_id=i['sendgrid_template_id']
            email_after_wm_subject=i['template_subject']
            email_after_wm_body=i['template_body']
            email_after_wm_delay=i['template_delay']
        if i['template_name'] == 'followup_1_email':
            send_followup1_email=i['send_email_after']
            automate_followup1_email=i['automate_after_email']
            followup1_email_sendgrid_template_id=i['sendgrid_template_id']
            followup1_email_subject=i['template_subject']
            followup1_email_body=i['template_body']
            followup1_email_delay=i['template_delay']
        if i['template_name'] == 'followup_2_email':
            send_followup2_email=i['send_email_after']
            automate_followup2_email=i['automate_after_email']
            followup2_email_sendgrid_template_id=i['sendgrid_template_id']
            followup2_email_subject=i['template_subject']
            followup2_email_body=i['template_body']
            followup2_email_delay=i['template_delay']
        if i['template_name'] == 'followup_3_email':
            send_followup3_email=i['send_email_after']
            automate_followup3_email=i['automate_after_email']
            followup3_email_sendgrid_template_id=i['sendgrid_template_id']
            followup3_email_subject=i['template_subject']
            followup3_email_body=i['template_body']
            followup3_email_delay=i['template_delay']
        

    campaign_insert_stmt="insert into campaign ( \
                              id \
                            , dateadded \
                            , janium_campaign_type_id \
                            , name \
                            , isactive \
                            , clientid \
                            , send_email_after_c \
                            , automate_email_after_c \
                            , email_after_c_sendgrid_template_id \
                            , email_after_c_subject \
                            , email_after_c_body \
                            , email_after_c_delay \
                            , send_email_after_wm \
                            , automate_email_after_wm \
                            , email_after_wm_sendgrid_template_id \
                            , email_after_wm_subject \
                            , email_after_wm_body \
                            , email_after_wm_delay \
                            , send_followup1_email \
                            , automate_followup1_email \
                            , followup1_email_sendgrid_template_id \
                            , followup1_email_subject \
                            , followup1_email_body \
                            , followup1_email_delay \
                            , send_followup2_email \
                            , automate_followup2_email \
                            , followup2_email_sendgrid_template_id \
                            , followup2_email_subject \
                            , followup2_email_body \
                            , followup2_email_delay \
                            , send_followup3_email \
                            , automate_followup3_email \
                            , followup3_email_sendgrid_template_id \
                            , followup3_email_subject \
                            , followup3_email_body \
                            , followup3_email_delay) \
                            values ( \
                              '{id}' \
                            , now() \
                            , 'NA' \
                            , '{campaign_name}' \
                            , 0 \
                            , '{clientid}' \
                            , case when '{send_email_after_c}' = 'None' then null else '{send_email_after_c}' end \
                            , case when '{automate_email_after_c}' = 'None' then null else '{automate_email_after_c}' end \
                            , case when '{email_after_c_sendgrid_template_id}' = 'None' then null else '{email_after_c_sendgrid_template_id}' end \
                            , case when '{email_after_c_subject}' = 'None' then null else '{email_after_c_subject}' end \
                            , case when '{email_after_c_body}' = 'None' then null else '{email_after_c_body}' end \
                            , case when '{email_after_c_delay}' = 'None' then null else '{email_after_c_delay}' end \
                            , case when '{send_email_after_wm}' = 'None' then null else '{send_email_after_wm}' end \
                            , case when '{automate_email_after_wm}' = 'None' then null else '{automate_email_after_wm}' end \
                            , case when '{email_after_wm_sendgrid_template_id}' = 'None' then null else '{email_after_wm_sendgrid_template_id}' end \
                            , case when '{email_after_wm_subject}' = 'None' then null else '{email_after_wm_subject}' end \
                            , case when '{email_after_wm_body}' = 'None' then null else '{email_after_wm_body}' end \
                            , case when '{email_after_wm_delay}' = 'None' then null else '{email_after_wm_delay}' end \
                            , case when '{send_followup1_email}' = 'None' then null else '{send_followup1_email}' end \
                            , case when '{automate_followup1_email}' = 'None' then null else '{automate_followup1_email}' end \
                            , case when '{followup1_email_sendgrid_template_id}' = 'None' then null else '{followup1_email_sendgrid_template_id}' end \
                            , case when '{followup1_email_subject}' = 'None' then null else '{followup1_email_subject}' end \
                            , case when '{followup1_email_body}' = 'None' then null else '{followup1_email_body}' end \
                            , case when '{followup1_email_delay}' = 'None' then null else '{followup1_email_delay}' end \
                            , case when '{send_followup2_email}' = 'None' then null else '{send_followup2_email}' end \
                            , case when '{automate_followup2_email}' = 'None' then null else '{automate_followup2_email}' end \
                            , case when '{followup2_email_sendgrid_template_id}' = 'None' then null else '{followup2_email_sendgrid_template_id}' end \
                            , case when '{followup2_email_subject}' = 'None' then null else '{followup2_email_subject}' end \
                            , case when '{followup2_email_body}' = 'None' then null else '{followup2_email_body}' end \
                            , case when '{followup2_email_delay}' = 'None' then null else '{followup2_email_delay}' end \
                            , case when '{send_followup3_email}' = 'None' then null else '{send_followup3_email}' end \
                            , case when '{automate_followup3_email}' = 'None' then null else '{automate_followup3_email}' end \
                            , case when '{followup3_email_sendgrid_template_id}' = 'None' then null else '{followup3_email_sendgrid_template_id}' end \
                            , case when '{followup3_email_subject}' = 'None' then null else '{followup3_email_subject}' end \
                            , case when '{followup3_email_body}' = 'None' then null else '{followup3_email_body}' end \
                            , case when '{followup3_email_delay}' = 'None' then null else '{followup3_email_delay}' end);".format(
                                  id=new_id
                                , clientid=account_id
                                , campaign_name=campaign_name
                                , send_email_after_c=send_email_after_c
                                , automate_email_after_c=automate_email_after_c
                                , email_after_c_sendgrid_template_id=email_after_c_sendgrid_template_id
                                , email_after_c_subject=email_after_c_subject
                                , email_after_c_body=email_after_c_body
                                , email_after_c_delay=email_after_c_delay
                                , send_email_after_wm=send_email_after_wm
                                , automate_email_after_wm=automate_email_after_wm
                                , email_after_wm_sendgrid_template_id=email_after_wm_sendgrid_template_id
                                , email_after_wm_subject=email_after_wm_subject
                                , email_after_wm_body=email_after_wm_body
                                , email_after_wm_delay=email_after_wm_delay
                                , send_followup1_email=send_followup1_email
                                , automate_followup1_email=automate_followup1_email
                                , followup1_email_sendgrid_template_id=followup1_email_sendgrid_template_id
                                , followup1_email_subject=followup1_email_subject
                                , followup1_email_body=followup1_email_body
                                , followup1_email_delay=followup1_email_delay
                                , send_followup2_email=send_followup2_email
                                , automate_followup2_email=automate_followup2_email
                                , followup2_email_sendgrid_template_id=followup2_email_sendgrid_template_id
                                , followup2_email_subject=followup2_email_subject
                                , followup2_email_body=followup2_email_body
                                , followup2_email_delay=followup2_email_delay
                                , send_followup3_email=send_followup3_email
                                , automate_followup3_email=automate_followup3_email
                                , followup3_email_sendgrid_template_id=followup3_email_sendgrid_template_id
                                , followup3_email_subject=followup3_email_subject
                                , followup3_email_body=followup3_email_body
                                , followup3_email_delay=followup3_email_delay
                            )
    print(campaign_insert_stmt)
    cursor.execute(campaign_insert_stmt)
    db.commit()
    cursor.close()
    db.close()
    return jsonify(message="Campaign Created", campaign_id=new_id)


@app.route('/api/v1/update_campaign/<string:account_id>/<string:campaign_id>', methods=['PUT'])
@jwt_required()
def update_campaign(account_id:str, campaign_id:str):
    jwt_data=jwt_token(request.headers.get('authorization'))
    db = conn()
    cursor=db.cursor()

    chk_permissions = "select count(*) from user_account_map where user_id = '{}' and client_id = '{}';".format(jwt_data['uid'], account_id)
    cursor.execute(chk_permissions)
    for i in cursor:
        chk_cnt = i[0]

    if chk_cnt == 0:
        cursor.close()
        db.close()
        return jsonify(message="User does not have permissions to update campaigns for this Account."), 402

    campaign=request.json

    check_campaign_qry="select count(*) from client c join campaign ca on c.id = ca.clientid where c.id = '{}' and ca.id = '{}';".format(account_id, campaign_id)
    print(check_campaign_qry)
    cursor.execute(check_campaign_qry)
    for i in cursor:
        cmpgn_chk=i[0]

    if cmpgn_chk == 0:
        cursor.close()
        db.close()
        return jsonify(message="Campaign by that ID does not exist.")
    
    new_id=uuid.uuid1()
    for i in campaign['campaign_info']:
        if i['template_name'] == 'after_campaign':
            send_email_after_c=i['send_email_after']
            automate_email_after_c=i['automate_after_email']
            email_after_c_sendgrid_template_id=i['sendgrid_template_id']
            email_after_c_subject=i['template_subject']
            email_after_c_body=i['template_body']
            email_after_c_delay=i['template_delay']
        if i['template_name'] == 'after_welcome_message':
            send_email_after_wm=i['send_email_after']
            automate_email_after_wm=i['automate_after_email']
            email_after_wm_sendgrid_template_id=i['sendgrid_template_id']
            email_after_wm_subject=i['template_subject']
            email_after_wm_body=i['template_body']
            email_after_wm_delay=i['template_delay']
        if i['template_name'] == 'followup_1_email':
            send_followup1_email=i['send_email_after']
            automate_followup1_email=i['automate_after_email']
            followup1_email_sendgrid_template_id=i['sendgrid_template_id']
            followup1_email_subject=i['template_subject']
            followup1_email_body=i['template_body']
            followup1_email_delay=i['template_delay']
        if i['template_name'] == 'followup_2_email':
            send_followup2_email=i['send_email_after']
            automate_followup2_email=i['automate_after_email']
            followup2_email_sendgrid_template_id=i['sendgrid_template_id']
            followup2_email_subject=i['template_subject']
            followup2_email_body=i['template_body']
            followup2_email_delay=i['template_delay']
        if i['template_name'] == 'followup_3_email':
            send_followup3_email=i['send_email_after']
            automate_followup3_email=i['automate_after_email']
            followup3_email_sendgrid_template_id=i['sendgrid_template_id']
            followup3_email_subject=i['template_subject']
            followup3_email_body=i['template_body']
            followup3_email_delay=i['template_delay']
        

    campaign_update_stmt="update campaign set \
                              send_email_after_c = case when '{send_email_after_c}' = 'None' then null else '{send_email_after_c}' end \
                            , automate_email_after_c = case when '{automate_email_after_c}' = 'None' then null else '{automate_email_after_c}' end \
                            , email_after_c_sendgrid_template_id = case when '{email_after_c_sendgrid_template_id}' = 'None' then null else '{email_after_c_sendgrid_template_id}' end \
                            , email_after_c_subject = case when '{email_after_c_subject}' = 'None' then null else '{email_after_c_subject}' end \
                            , email_after_c_body = case when '{email_after_c_body}' = 'None' then null else '{email_after_c_body}' end \
                            , email_after_c_delay = case when '{email_after_c_delay}' = 'None' then null else '{email_after_c_delay}' end \
                            , send_email_after_wm = case when '{send_email_after_wm}' = 'None' then null else '{send_email_after_wm}' end \
                            , automate_email_after_wm = case when '{automate_email_after_wm}' = 'None' then null else '{automate_email_after_wm}' end \
                            , email_after_wm_sendgrid_template_id = case when '{email_after_wm_sendgrid_template_id}' = 'None' then null else '{email_after_wm_sendgrid_template_id}' end \
                            , email_after_wm_subject = case when '{email_after_wm_subject}' = 'None' then null else '{email_after_wm_subject}' end \
                            , email_after_wm_body = case when '{email_after_wm_body}' = 'None' then null else '{email_after_wm_body}' end \
                            , email_after_wm_delay = case when '{email_after_wm_delay}' = 'None' then null else '{email_after_wm_delay}' end \
                            , send_followup1_email = case when '{send_followup1_email}' = 'None' then null else '{send_followup1_email}' end \
                            , automate_followup1_email = case when '{automate_followup1_email}' = 'None' then null else '{automate_followup1_email}' end \
                            , followup1_email_sendgrid_template_id = case when '{followup1_email_sendgrid_template_id}' = 'None' then null else '{followup1_email_sendgrid_template_id}' end \
                            , followup1_email_subject = case when '{followup1_email_subject}' = 'None' then null else '{followup1_email_subject}' end \
                            , followup1_email_body = case when '{followup1_email_body}' = 'None' then null else '{followup1_email_body}' end \
                            , followup1_email_delay = case when '{followup1_email_delay}' = 'None' then null else '{followup1_email_delay}' end \
                            , send_followup2_email = case when '{send_followup2_email}' = 'None' then null else '{send_followup2_email}' end \
                            , automate_followup2_email = case when '{automate_followup2_email}' = 'None' then null else '{automate_followup2_email}' end \
                            , followup2_email_sendgrid_template_id = case when '{followup2_email_sendgrid_template_id}' = 'None' then null else '{followup2_email_sendgrid_template_id}' end \
                            , followup2_email_subject = case when '{followup2_email_subject}' = 'None' then null else '{followup2_email_subject}' end \
                            , followup2_email_body = case when '{followup2_email_body}' = 'None' then null else '{followup2_email_body}' end \
                            , followup2_email_delay = case when '{followup2_email_delay}' = 'None' then null else '{followup2_email_delay}' end \
                            , send_followup3_email = case when '{send_followup3_email}' = 'None' then null else '{send_followup3_email}' end \
                            , automate_followup3_email = case when '{automate_followup3_email}' = 'None' then null else '{automate_followup3_email}' end \
                            , followup3_email_sendgrid_template_id = case when '{followup3_email_sendgrid_template_id}' = 'None' then null else '{followup3_email_sendgrid_template_id}' end \
                            , followup3_email_subject = case when '{followup3_email_subject}' = 'None' then null else '{followup3_email_subject}' end \
                            , followup3_email_body = case when '{followup3_email_body}' = 'None' then null else '{followup3_email_body}' end \
                            , followup3_email_delay = case when '{followup3_email_delay}' = 'None' then null else '{followup3_email_delay}' end \
                            where id = '{id}';".format(
                                  id=campaign_id
                                , send_email_after_c=send_email_after_c
                                , automate_email_after_c=automate_email_after_c
                                , email_after_c_sendgrid_template_id=email_after_c_sendgrid_template_id
                                , email_after_c_subject=email_after_c_subject
                                , email_after_c_body=email_after_c_body
                                , email_after_c_delay=email_after_c_delay
                                , send_email_after_wm=send_email_after_wm
                                , automate_email_after_wm=automate_email_after_wm
                                , email_after_wm_sendgrid_template_id=email_after_wm_sendgrid_template_id
                                , email_after_wm_subject=email_after_wm_subject
                                , email_after_wm_body=email_after_wm_body
                                , email_after_wm_delay=email_after_wm_delay
                                , send_followup1_email=send_followup1_email
                                , automate_followup1_email=automate_followup1_email
                                , followup1_email_sendgrid_template_id=followup1_email_sendgrid_template_id
                                , followup1_email_subject=followup1_email_subject
                                , followup1_email_body=followup1_email_body
                                , followup1_email_delay=followup1_email_delay
                                , send_followup2_email=send_followup2_email
                                , automate_followup2_email=automate_followup2_email
                                , followup2_email_sendgrid_template_id=followup2_email_sendgrid_template_id
                                , followup2_email_subject=followup2_email_subject
                                , followup2_email_body=followup2_email_body
                                , followup2_email_delay=followup2_email_delay
                                , send_followup3_email=send_followup3_email
                                , automate_followup3_email=automate_followup3_email
                                , followup3_email_sendgrid_template_id=followup3_email_sendgrid_template_id
                                , followup3_email_subject=followup3_email_subject
                                , followup3_email_body=followup3_email_body
                                , followup3_email_delay=followup3_email_delay
                            )
    print(campaign_update_stmt)
    cursor.execute(campaign_update_stmt)
    db.commit()
    cursor.close()
    db.close()
    return jsonify(message="Campaign Sucessfully Updated")


@app.route('/update_password', methods=['PUT'])
@jwt_required()
def update_password():
    # need logic to send an email to the user so that they can update the password from a link that is sent to them.
    # this will only be for those that know their current password.
    oldPassword = request.args.get('oldPassword')
    newPassword = request.args.get('newPassword')

    jwt_token=request.headers.get('authorization')
    jwt_data=jwt_1.decode(jwt_token[7:], jwt_access_key, algorithms=jwt_algos)

    # Check to see if the user is who has been sent from the token.
    check_old_pwd="select count(*) from client c join credentials cr on c.id = cr.client_id where c.id = '{}' and c.email = '{}' and cr.credential = '{}';".format(jwt_data['uid'], jwt_data['sub'], oldPassword)
    print(check_old_pwd)

    db = conn()
    cursor=db.cursor()
    cursor.execute(check_old_pwd)
    for i in cursor:
        pwd_check=i[0]
    if pwd_check > 0:
        update_password="update credentials set credential = '{}' where client_id = '{}';".format(newPassword, jwt_data['uid'])
        print(update_password)
        cursor.execute(update_password)
        db.commit()
        cursor.close()
        db.close()
        return jsonify(message="Sucessfully Updated Password!")
    else:
        cursor.close()
        db.close()
        return jsonify(message="Old password did not match, please re-enter the correct password that is being changed from."), 401


# Used to update a users permissions
@app.route('/update_permissions')
def update_permissions():
    pass


if __name__ == '__main__':
    app.run()