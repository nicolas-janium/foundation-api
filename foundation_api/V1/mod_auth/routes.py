from datetime import datetime, timezone
from uuid import uuid4
from threading import Thread

from flask import Blueprint, jsonify, request, make_response, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token, set_access_cookies, unset_jwt_cookies
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from foundation_api import bcrypt, mail, check_json_header
from foundation_api.V1.sa_db.model import db
from foundation_api.V1.sa_db.model import User, Account, Time_zone, Credentials, Dte

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
@check_json_header
def create_user():
    """
        required JSON keys: username, password, first_name, last_name, title, company, 
        time_zone_code (US/Mountain, US/Pacific, US/Central, US/Eastern)
    """
    if json_body := request.get_json():
        if existing_username := db.session.query(Credentials).filter(Credentials.username == json_body['username']).first():
            return make_response(jsonify({"message": "Username already exists"}), 409)
        
        if time_zone := db.session.query(Time_zone).filter(Time_zone.time_zone_code == json_body['time_zone_code']).first():
            time_zone_id = time_zone.time_zone_id
            credentials_id = str(uuid4())
            credentials = Credentials(
                credentials_id,
                json_body['username'],
                bcrypt.generate_password_hash(json_body['password']).decode("utf-8")
            )
            db.session.add(credentials)
            # db.session.commit()
            
            user_id = str(uuid4())
            user = User(
                user_id,
                credentials_id,
                json_body['first_name'],
                json_body['last_name'],
                json_body['title'],
                json_body['company'],
                None,
                json_body['username'],
                None,
                None
            )
            db.session.add(user)
            # db.session.commit()
 
            account = Account(
                str(uuid4()),
                user_id,
                False,
                False,
                False,
                datetime.utcnow(),
                datetime.utcnow(),
                datetime.utcnow(),
                datetime.utcnow(),
                time_zone_id,
                Dte.unassigned_dte_id
            )
            db.session.add(account)
            db.session.commit()

            return jsonify({"message": "success"})
        return make_response(jsonify({"message": "Invalid time_zone_code"}), 422)
    return make_response(jsonify({"message": "Missing JSON body"}), 422)

@mod_auth.route('/login', methods=['POST'])
def login_user():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({"message": "Missing username or password"}), 401)

    if credentials := db.session.query(Credentials).filter(Credentials.username == auth.username).first():
        if bcrypt.check_password_hash(credentials.password, auth.password):
            user = credentials.credentials_user
            access_token = create_access_token(identity=user.user_id)
            refresh_token = create_refresh_token(identity=user.user_id)
            response = make_response(jsonify({"message": "success", "access_token": access_token, "refresh_token": refresh_token}), 200)
            return response
        else:
            return make_response(jsonify({"message": "Incorrect Password"}), 401)
    else:
        return make_response(jsonify({"message": "Username not found"}), 401)

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
            return jsonify({"message": "success"})
        else:
            return make_response(jsonify({"message": "Missing JSON body"}), 422)
    else:
        return make_response(jsonify({"message": "Username not found"}), 401)

### Logging out will happen solely on the react app ###
# @mod_auth.route('/logout', methods=['POST'])
# @jwt_required()
# def logout_user():
#     user_id = get_jwt_identity() # Get user_id value directly from the jwt

#     response = make_response(jsonify({"message": "User logged out successfully"}), 200)
#     unset_jwt_cookies(response)
#     return response

# @mod_auth.route('/get_user', methods=['GET'])
# @jwt_required()
# def get_user():
#     user_id = get_jwt_identity() # Get user_id value directly from the jwt
#     if user := db.session.query(User).filter(User.user_id == user_id).first():
#         return jsonify({
#             "user_id": user_id,
#             "full_name": user.full_name,
#             "title": user.title,
#             "company": user.company,
#             "location": user.location,
#             "primary_email": user.primary_email,
#             "campaign_management_email": user.campaign_management_email,
#             "alternate_dte_email": user.alternate_dte_email,
#             "phone": user.phone
#         })
#     else:
#         return make_response(jsonify({"message": "User does not exist"}), 401)

"""
On which service does the reset password functionality live? The react app or the flask app?
I suggest on the react app. We create an endpoint that swaps the passwords
"""

# def send_reset_email(app, token, email):
#     with current_app.app_context():
#         mail.send_email(
#             from_email=app.config['SENDGRID_DEFAULT_FROM'],
#             to_email=email,
#             subject="Password Reset Request",
#             text=token ### Need to generate simple email body that contains the link with the token ###
#         )

# @mod_auth.route('/reset_user_password', methods=['POST'])
# def reset_user_password_request():
#     json_body = request.get_json()
#     username = json_body['username']
#     user_email = json_body['email']
#     if user := db.session.query(User).filter(User.username == username).first():

#         ### Create token to be sent in email ###
#         s = Serializer(current_app.config['SECRET_KEY'], 1800)
#         token = s.dumps({'user_id': user.user_id}).decode('utf-8')

#         ### Send email asynchronously ###
#         Thread(target=send_reset_email, args=(current_app, token, user_email)).start()

#         return jsonify({"message": "Reset password email sent"})
#     else:
#         return make_response(jsonify({"message": "User does not exist"}), 401)

# @mod_auth.route('/reset_user_password/<token>', methods=['PUT'])
# def reset_user_password(token):
#     json_body = request.get_json()
#     new_password = json_body['password']

#     ### Decode token and see if valid. User_id in token ###
#     s = Serializer(current_app.config['SECRET_KEY'])
#     if user_id := s.loads(token)['user_id']:

#         if user := db.session.query(User).filter(User.user_id == user_id).first():
#             hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
#             user.password = hashed_password
#             db.session.commit()
#             return jsonify({"message": "Password has been reset"})
#         else:
#             return make_response(jsonify({"message": "User does not exist"}), 401)
#     else:
#         return make_response(jsonify({"message": "Invalid or expired token"}), 401)
