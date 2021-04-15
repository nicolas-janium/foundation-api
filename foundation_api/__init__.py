from flask import Flask
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_sendgrid import SendGrid
from flask_sqlalchemy import SQLAlchemy
import os

# Define the WSGI application object
app = Flask(__name__)

# Configurations
app.config.from_object('config')

# Define the database object which is imported
# by modules and controllers
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://nicolas:nicolas113112@localhost/dev"
db = SQLAlchemy(app)
# db.create_all()

jwt = JWTManager(app)
bcrypt = Bcrypt(app)

mail = SendGrid(app)

from foundation_api.V1.mod_auth.routes import mod_auth as auth_module
from foundation_api.V1.mod_account.routes import mod_account as account_module

# Register blueprint(s)
app.register_blueprint(auth_module)
app.register_blueprint(account_module)