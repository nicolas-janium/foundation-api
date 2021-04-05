from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt

# Define the WSGI application object
app = Flask(__name__)

# Configurations
app.config.from_object('config')

# Define the database object which is imported
# by modules and controllers
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://nicolas:nicolas113112@localhost/dev"
db = SQLAlchemy(app)
db.create_all()

jwt = JWTManager(app)
bcrypt = Bcrypt(app)

from foundation_api.V1.mod_hello.routes import mod_hello as hello_module
from foundation_api.V1.mod_auth.routes import mod_auth as auth_module

# Register blueprint(s)
app.register_blueprint(hello_module)
app.register_blueprint(auth_module)
