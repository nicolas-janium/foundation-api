import os

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_sendgrid import SendGrid
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
# from flask_wtf.csrf import CSRFProtect, generate_csrf

# Define the WSGI application object
app = Flask(__name__)
CORS(app)

# Configurations
app.config.from_object('config')

# Define the database object which is imported
# by modules and controllers
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://nicolas:nicolas113112@localhost/dev"
db = SQLAlchemy(app)
# db.create_all()

# csrf = CSRFProtect(app)
# @app.after_request
# def set_csrf_token(response):
#     response.set_cookie('csrf_token', generate_csrf())
#     return response

jwt = JWTManager(app)
bcrypt = Bcrypt(app)

mail = SendGrid(app)

from foundation_api.V1.mod_auth.routes import mod_auth as auth_module
from foundation_api.V1.mod_campaign.routes import mod_campaign as campaign_module
from foundation_api.V1.mod_home.routes import mod_home as home_module
from foundation_api.V1.mod_onboard.routes import mod_onboard as onboard_module
from foundation_api.V1.mod_jobs.routes import mod_jobs as jobs_module
from foundation_api.V1.mod_email.routes import mod_email as email_module
from foundation_api.V1.mod_tasks.routes import mod_tasks as tasks_module


# Register blueprint(s)
app.register_blueprint(auth_module)
app.register_blueprint(onboard_module)
app.register_blueprint(home_module)
app.register_blueprint(campaign_module)
app.register_blueprint(jobs_module)
app.register_blueprint(tasks_module)
app.register_blueprint(email_module)