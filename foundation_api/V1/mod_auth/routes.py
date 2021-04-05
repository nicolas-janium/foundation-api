import os
import random
import string
import uuid
from datetime import timedelta, datetime

from flask import Blueprint, request

from foundation_api import db
from foundation_api import app
from foundation_api import bcrypt
from foundation_api.V1.mod_auth.models import User

mod_auth = Blueprint('auth', __name__, url_prefix='/api/v1')

@mod_auth.route('/', methods=['GET'])
def hello_auth():
    return "Hello auth_module!"

@mod_auth.route('/signup', methods=['POST'])
def create_user():
    json_body = request.get_json()

    if existing_user := db.session.query(User).filter(User.)