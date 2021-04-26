import os
import random
import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from threading import Thread

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity, create_refresh_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from flask_mail import Message
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_auth.models import User, Account, User_account_map, Account_group, Time_zone, Permission

mod_auth = Blueprint('auth', __name__, url_prefix='/api/v1')

"""
Evan will have to have logic on the front-end to handle expired jwt's. If expired,
send request to /refresh_access_token. If both are expired, requires new user login
"""
### We are using the `refresh=True` option in jwt_required to only allow ###
### refresh tokens to access this route. ###
@mod_auth.route("/refresh_token", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    access_token = create_access_token(identity=get_jwt_identity())
    response = make_response(jsonify({"message": "Access token refreshed"}), 200)
    set_access_cookies(response, access_token)
    return response

@mod_auth.route('/signup', methods=['POST'])
def create_user():
    json_body = request.get_json(force=True)
    username = json_body['username']
    password = json_body['password']

    if existing_user := db.session.query(User).filter(User.username == username).first(): # Returns None or User object
        return make_response(jsonify({"message": "Username taken"}), 401)
    
    time_zone_id = db.session.query(Time_zone).filter(Time_zone.time_zone_code == json_body['time_zone_code']).first().time_zone_id

    new_user_id = str(uuid4())
    new_user = User(
        new_user_id,
        json_body['first_name'],
        json_body['last_name'],
        json_body['title'],
        json_body['company'],
        None,
        username,
        None,
        None,
        # '1c914a6c-6168-47a8-8460-93c865b1888a', # What should the updated_by value be for new users?
        User.system_user_id,
        username,
        bcrypt.generate_password_hash(password).decode("utf-8")
    )
    db.session.add(new_user)

    new_account_id = str(uuid4())
    new_account = Account(
        new_account_id,
        Account_group.unassigned_account_group_id,
        False,
        False,
        False,
        datetime.utcnow(),
        datetime.utcnow(),
        datetime.utcnow(),
        datetime.utcnow(),
        time_zone_id,
        User.system_user_id,
        1
    )
    db.session.add(new_account)

    user_account_map = User_account_map(
        new_user_id, 
        new_account_id,
        Permission.default_permission_id
    )
    db.session.add(user_account_map)
    db.session.commit()

    return jsonify({"message": "User created successfully"})

    # access_token = create_access_token(identity=new_user_id)
    # refresh_token = create_refresh_token(identity=new_user_id)

    # response = make_response(jsonify({"message": "User created successfully", "access_token": access_token, "refresh_token": refresh_token}), 200)
    # # set_access_cookies(response, access_token)
    # # set_refresh_cookies(response, refresh_token)
    # return response

@mod_auth.route('/login', methods=['POST'])
def login_user():
    json_body = request.get_json()
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({"message": "Could not verify"}), 401)

    if user := db.session.query(User).filter(User.username == auth.username).first():
        if bcrypt.check_password_hash(user.password, auth.password):
            access_token = create_access_token(identity=user.user_id)
            refresh_token = create_refresh_token(identity=user.user_id)
            # response = make_response(jsonify({"message": "Login successfull"}), 200)
            response = make_response(jsonify({"message": "Login successfull", "access_token": access_token, "refresh_token": refresh_token}), 200)
            # response = set_csrf_token(response)
            # set_access_cookies(response, access_token)
            # set_refresh_cookies(response, refresh_token)
            return response
        else:
            return make_response(jsonify({"message": "Incorrect Password"}), 401)
    else:
        return make_response(jsonify({"message": "User does not exist"}), 401)

@mod_auth.route('/logout', methods=['DELETE'])
@jwt_required()
def logout_user():
    user_id = get_jwt_identity() # Get user_id value directly from the jwt

    response = make_response(jsonify({"message": "User logged out successfully"}), 200)
    unset_jwt_cookies(response)
    return response

@mod_auth.route('/update_user', methods=['PUT'])
@jwt_required()
def update_user():
    user_id = get_jwt_identity() # Get user_id value directly from the jwt

    if user := db.session.query(User).filter(User.user_id == user_id).first(): # Returns None or User object
        if json_body := request.get_json():
            user.first_name = json_body['first_name']
            user.last_name = json_body['last_name']
            user.title = json_body['title']
            user.company = json_body['company']
            user.location = json_body['location']
            user.additional_contact_info = json_body['additional_contact_info']
            user.phone = json_body['phone']
            db.session.commit()
            return jsonify({"message": "User updated"})
        else:
            return make_response(jsonify({"message": "Missing JSON body"}), 400)
    else:
        return make_response(jsonify({"message": "User does not exist"}), 401)



    json_body = request.get_json(force=True)
    username = json_body['username']
    password = json_body['password']

    if existing_user := db.session.query(User).filter(User.username == username).first():
        return make_response(jsonify({"message": "The user already exists"}), 401)
    
    new_user_id = str(uuid4())
    new_user = User(
        new_user_id,
        json_body['first_name'],
        json_body['last_name'],
        json_body['title'],
        json_body['company'],
        json_body['location'],
        json_body['primary_email'],
        None,
        json_body['phone'],
        '1c914a6c-6168-47a8-8460-93c865b1888a', # What should the updated_by value be for new users?
        # new_user_id,
        username,
        bcrypt.generate_password_hash(password).decode("utf-8")
    )
    db.session.add(new_user)
    db.session.commit()

    additional_token_data = {"user_id": new_user_id}
    access_token = create_access_token(identity=username, additional_claims=additional_token_data)
    return jsonify({"message": "User created successfully", "access_token": access_token})


@mod_auth.route('/get_user', methods=['GET'])
@jwt_required()
def get_user():
    user_id = get_jwt_identity() # Get user_id value directly from the jwt
    if user := db.session.query(User).filter(User.user_id == user_id).first():
        return jsonify({
            "user_id": user_id,
            "full_name": user.full_name,
            "title": user.title,
            "company": user.company,
            "location": user.location,
            "primary_email": user.primary_email,
            "campaign_management_email": user.campaign_management_email,
            "alternate_dte_email": user.alternate_dte_email,
            "phone": user.phone
        })
    else:
        return make_response(jsonify({"message": "User does not exist"}), 401)

"""
On which service does the reset password functionality live? The react app or the flask app?
I suggest on the react app. We create an endpoint that swaps the passwords
"""

def send_reset_email(app, token, email):
    with app.app_context():
        mail.send_email(
            from_email=app.config['SENDGRID_DEFAULT_FROM'],
            to_email=email,
            subject="Password Reset Request",
            text=token ### Need to generate simple email body that contains the link with the token ###
        )

@mod_auth.route('/reset_user_password', methods=['POST'])
def reset_user_password_request():
    json_body = request.get_json()
    username = json_body['username']
    user_email = json_body['email']
    if user := db.session.query(User).filter(User.username == username).first():

        ### Create token to be sent in email ###
        s = Serializer(app.config['SECRET_KEY'], 1800)
        token = s.dumps({'user_id': user.user_id}).decode('utf-8')

        ### Send email asynchronously ###
        Thread(target=send_reset_email, args=(app, token, user_email)).start()

        return jsonify({"message": "Reset password email sent"})
    else:
        return make_response(jsonify({"message": "User does not exist"}), 401)

@mod_auth.route('/reset_user_password/<token>', methods=['PUT'])
def reset_user_password(token):
    json_body = request.get_json()
    new_password = json_body['password']

    ### Decode token and see if valid. User_id in token ###
    s = Serializer(app.config['SECRET_KEY'])
    if user_id := s.loads(token)['user_id']:

        if user := db.session.query(User).filter(User.user_id == user_id).first():
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            user.password = hashed_password
            db.session.commit()
            return jsonify({"message": "Password has been reset"})
        else:
            return make_response(jsonify({"message": "User does not exist"}), 401)
    else:
        return make_response(jsonify({"message": "Invalid or expired token"}), 401)
