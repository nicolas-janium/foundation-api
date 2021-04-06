from flask import Blueprint, Flask, jsonify, request, render_template
import sys
sys.path.append("../")
from Database.model import User, LoginCredential
from Database.model import db
import uuid
import logging
from datetime import datetime,timezone
import datetime as dttm
import sqlalchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token


app = Flask(__name__)
jwt = JWTManager(app)


v1_login_user = Blueprint('v1_login_user',__name__)
@v1_login_user.route("/api/v1/login_user", methods=['POST'])
def login_user():
    print('Request: ', request.get_json)
    req_json = request.get_json()
    dt = datetime.utcnow()
    dt_format = dt.strftime("%Y-%m-%d %H:%M:%S")
    # if request.is_json:
    #     email = request.json['email']
    #     password = request.json['password']
    # else:
    #     email = request.form['email']
    #     password = request.form['password']

    print (req_json)
    email=req_json['email']
    password=req_json['password']
    print(email)
    print(password)

    qry = User.query \
        .join(LoginCredential, User.user_id == LoginCredential.user_id) \
        .add_columns(User.user_id,LoginCredential.credential) \
        .filter(LoginCredential.asOfStartTime <= dt_format) \
        .filter(LoginCredential.asOfEndTime > dt_format) \
        .first()

    if qry.credential == password:
        login_flag = True
    else:
        login_flag = False
        
    if login_flag:
        additional_data={"uid": qry.user_id}

        access_token = create_access_token(identity=email, additional_claims=additional_data)
        return jsonify(message="Login succeeded!", access_token=access_token, auth_token=access_token)

    else:
        return jsonify(message="Bad email or password"), 401

    