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

v1_get_user = Blueprint('v1_get_user',__name__)
@v1_get_user.route("/api/v1/get_user/<user_id>", methods=['POST'])
def get_user(user_id):
    print(request)
    req_json = request.get_json()
    print(req_json)
    dt = datetime.utcnow()
    dt_format = dt.strftime("%Y-%m-%d %H:%M:%S")

    qry = User.query \
        .add_columns(User.user_id,User.first_name,User.last_name,User.location,User.phone,User.title) \
        .filter(User.asOfStartTime <= dt_format) \
        .filter(User.asOfEndTime > dt_format) \
        .filter(User.user_id == user_id) \
        .first()

    account_qry = User.query \
        .join()

    ret = {}
    ret['firstName']=qry[2]
    ret['lastName']=qry[3]
    ret['location']=qry[4]
    ret['phone']=qry[5]
    ret['title']=qry[6]

    return jsonify(ret)