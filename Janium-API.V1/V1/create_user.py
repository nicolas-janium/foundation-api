from flask import Blueprint, Flask, jsonify, request, render_template
import sys
sys.path.append("../")
from Database.model import User
from Database.model import db
import uuid
import logging
from datetime import datetime,timezone
import datetime as dttm
import sqlalchemy

v1_create_user = Blueprint('v1_create_user',__name__)
@v1_create_user.route("/api/v1/create_user", methods=['POST'])
def create_user():
    email = request.args.get('email') or "<null>"
    accountEmail = request.args.get('accountEmail') or "<null>"
    ulincid = request.args.get('ulincid') or "<null>"
    ulinc_username = request.args.get('ulinc_username') or "<null>"
    ulinc_password = request.args.get('ulinc_password') or "<null>"
    logging.info('Customer Email: ', email)
    print(email)

    # # Check if user has privileges to create user.
    # jwt_token=request.headers.get('authorization')
    # jwt_data=jwt_1.decode(jwt_token[7:], jwt_access_key, algorithms=jwt_algos)

    qry = User.query.filter(User.primary_email == email).all()

    if len(qry) > 0:
        print('User Already Exists')
        return jsonify(message="User already exists")
    else:
        new_id=str(uuid.uuid1())
        dt=datetime.utcnow()
        print(new_id)
        usr = User(user_id=new_id
                    ,asOfStartTime=dt.strftime("%Y-%m-%d %H:%M:%S")
                    ,asOfEndTime='9999-12-31 10:10:10'
                    ,primary_email=email)
        db.session.add(usr)
        db.session.commit()
        return jsonify(message="User for email: {} has been created!".format(email))

    
