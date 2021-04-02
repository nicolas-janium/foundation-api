from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# Define the WSGI application object
app = Flask(__name__)

# Configurations
app.config.from_object('config')

# Define the database object which is imported
# by modules and controllers
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://nicolas:nicolas113112@localhost/dev"
db = SQLAlchemy(app)

jwt = JWTManager(app)

from foundation.mod_hello.routes import mod_hello as hello_module

# Register blueprint(s)
app.register_blueprint(hello_module)
