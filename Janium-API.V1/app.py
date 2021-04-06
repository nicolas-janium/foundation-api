from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import json
from Database.model import User,LoginCredential,Account,Account_Type,Email_Server
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime,ForeignKey,join
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from V1.create_user import v1_create_user
from V1.login_user import v1_login_user
from V1.get_user import v1_get_user
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from datetime import timedelta
from flask_cors import CORS
import jwt

app = Flask(__name__)
JWT = JWTManager(app)
db = SQLAlchemy(app)
CORS(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://api:api@localhost:3307/janium"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
jwt_access_key = 'super-secret'
app.config['JWT_SECRET_KEY'] = jwt_access_key 
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=10)
jwt_algos = ["HS256"]

### Register blueprints
app.register_blueprint(v1_create_user)
app.register_blueprint(v1_login_user)
app.register_blueprint(v1_get_user)

### Populate the Database with Type Values ###
Email_Server.initial_population()
User.initial_population()
LoginCredential.initial_population()
Account_Type.initial_population()
Account.initial_population()

@app.route("/")
def home():
    return jsonify(message='Hello')

def decodeAuthToken(token):
    try:
        payload = jwt.decode(token, jwt_access_key, algorithms=jwt_algos)
        return payload
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Login please'
    except jwt.InvalidTokenError:
        return 'Nice try, invalid token. Login please'

@app.route('/test_get_with_validation')
def testGetWithValidation():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        token = auth_header.split(" ")[1] # Parses out the "Bearer" portion
    else:
        token = ''

    # if token:
    #     decoded = decodeAuthToken(token)
    #     if not isinstance(decoded, str):
    #         if decoded['admin']:
    #             return jsonify('You Are a Real Admin!!')
    #         else:
    #             return jsonify('You Are not an Admin, but at least your token is valid!')
    #     else:
    #         return jsonify('Ooops, validation messed up: ' + decoded), 401

    return jsonify(message="Jello")

if __name__ == '__main__':
    app.run()

## Code to run docker mysql: docker run -d --publish=3307:3306 --name=mysql_janium -e MYSQL_ROOT_PASSWORD=root mysql/mysql-server:latest