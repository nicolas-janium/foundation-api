from datetime import datetime, timedelta, timezone
from uuid import uuid4
from threading import Thread

from flask import Blueprint, json, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_ulinc.models import User, Account, Ulinc_config
from foundation_api.V1.utils.ulinc import get_ulinc_client_info
from foundation_api.V1.utils.refresh_ulinc_data import refresh_ulinc_campaigns, refresh_ulinc_cookie


mod_ulinc = Blueprint('ulinc', __name__, url_prefix='/api/v1')

@mod_ulinc.route('/ulinc_config', methods=['PUT'])
@jwt_required()
def update_ulinc_config():
    """
    Required JSON keys: ulinc_config_id, 
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()
