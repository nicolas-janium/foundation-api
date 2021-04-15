import os
import random
import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from threading import Thread

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_campaign.models import User, Account, Ulinc_config, Credentials, Cookie, Contact, Action
from foundation_api.V1.utils.get_ulinc import get_ulinc_client_info

mod_campaign = Blueprint('campaign', __name__, url_prefix='/api/v1')

@mod_campaign.route('/create_janium_campaign', methods=['POST'])
@jwt_required()
def create_janium_campaign():
    """
    Required JSON keys: ulinc_username, ulinc_password, ulinc_li_email
    """