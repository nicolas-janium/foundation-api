import os
import random
import string
import uuid
from datetime import timedelta, datetime

from flask import Blueprint

from foundation import db
from foundation import app
from foundation.mod_hello.models import Action

mod_hello = Blueprint('hello', __name__, url_prefix='/')

@mod_hello.route('/', methods=['GET'])
def hello_world():
    new_action = Action(str(uuid.uuid4()),  '002c23a9-78ef-4e24-89cf-1a92a5686322', 11, datetime.utcnow(), None)
    db.session.add(new_action)
    db.session.commit()
    return "Action submitted"
