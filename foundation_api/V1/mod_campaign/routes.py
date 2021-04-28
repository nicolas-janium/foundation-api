import os
import random
import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from threading import Thread

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_campaign.models import User, Account, Ulinc_config, Credentials, Cookie, Contact, Action, Janium_campaign, Ulinc_campaign, Janium_campaign_step

mod_campaign = Blueprint('campaign', __name__, url_prefix='/api/v1')

@mod_campaign.route('/janium_campaigns', methods=['GET'])
@jwt_required()
def get_janium_campaigns():
    """
    Required query params: None
    """
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if janium_accounts := user.accounts:
        janium_account = janium_accounts[0].account # Users are only associated with one Janium Campaign

        janium_campaigns = []
        for janium_campaign in janium_account.janium_campaigns:
            janium_campaign_steps = []
            for janium_campaign_step in janium_campaign.janium_campaign_steps:
                janium_campaign_steps.append(
                    {
                        "janium_campaign_step_id": janium_campaign_step.janium_campaign_step_id,
                        "janium_campaign_step_type_id": janium_campaign_step.janium_campaign_step_type_id,
                        "janium_campaign_step_delay": janium_campaign_step.janium_campaign_step_delay,
                        "janium_campaign_step_body": janium_campaign_step.janium_campaign_step_body,
                        "janium_campaign_step_subject": janium_campaign_step.janium_campaign_step_subject
                    }
                )
            janium_campaigns.append(
                {
                    "janium_campaign_id": janium_campaign.janium_campaign_id,
                    "janium_campaign_name": janium_campaign.janium_campaign_name,
                    "janium_campaign_description": janium_campaign.janium_campaign_description,
                    "email_config_id": janium_campaign.email_config_id,
                    "queue_start_time": janium_campaign.queue_start_time,
                    "queue_end_time": janium_campaign.queue_end_time,
                    "janium_campaign_steps": janium_campaign_steps
                }
            )
        return jsonify(janium_campaigns)

@mod_campaign.route('/janium_campaign', methods=['GET'])
@jwt_required()
def get_janium_campaign():
    """
    Required query params: janium_campaign_id
    """
    json_body = request.get_json(force=True)
    janium_campaign_id = request.args.get('janium_campaign_id')
    user_id = get_jwt_identity()
    # user = db.session.query(User).filter(User.user_id == user_id).first()

    janium_campaign = db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == janium_campaign_id).first()

    return jsonify(
        {
            "janium_campaign_id": janium_campaign_id,
            "janium_campaign_name": janium_campaign.janium_campaign_name,
            "janium_campaign_description": janium_campaign.janium_campaign_description,
            "email_config_id": janium_campaign.email_config_id,
            "queue_start_time": janium_campaign.queue_start_time,
            "queue_end_time": janium_campaign.queue_end_time
        }
    )

@mod_campaign.route('/janium_campaign', methods=['POST'])
@jwt_required()
def create_janium_campaign():
    """
    Required JSON keys: ulinc_config_id, email_config_id, janium_campaign_name, janium_campaign_description, queue_start_time, queue_end_time
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if janium_accounts := user.accounts:
        janium_account = janium_accounts[0].account # Users are only associated with one Janium Campaign

        if db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_name == json_body['janium_campaign_name']).first():
            return jsonify({"message": "A Janium campaign with that name already exists"})

        new_janium_campaign = Janium_campaign(
            str(uuid4()),
            janium_account.account_id,
            json_body['ulinc_config_id'],
            json_body['email_config_id'],
            json_body['janium_campaign_name'],
            json_body['janium_campaign_description'],
            False, # Not doing messenger campaigns for the MVP
            False,
            json_body['queue_start_time'],
            json_body['queue_end_time'],
            user_id
        )
        db.session.add(new_janium_campaign)
        db.session.commit()
        return jsonify({"message": "Janium campaign created successfully"})

@mod_campaign.route('/janium_campaign', methods=['PUT'])
@jwt_required()
def update_janium_campaign():
    """
    Required JSON keys: janium_campaign_id, email_config_id, janium_campaign_name, janium_campaign_description, queue_start_time, queue_end_time
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    janium_campaign = db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == json_body['janium_campaign_id']).first()

    janium_campaign.janium_campaign_name = json_body['janium_campaign_name']
    janium_campaign.janium_campaign_description = json_body['janium_campaign_description']
    janium_campaign.email_config_id = json_body['email_config_id']
    janium_campaign.queue_start_time = json_body['queue_start_time']
    janium_campaign.queue_end_time = json_body['queue_end_time']
    db.session.commit()

    return jsonify({"message": "Janium campaign updated successfully"})

@mod_campaign.route('/janium_campaign_step', methods=['POST'])
@jwt_required()
def create_janium_campaign_step():
    """
    Required JSON keys: janium_campaign_id, janium_campaign_step_type (li_message, email, pre_connection_email, text), janium_campaign_step_delay,
    janium_campaign_step_body, janium_campaign_step_subject (if type == email or type == pre_connection_email), 
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    # user = db.session.query(User).filter(User.user_id == user_id).first()

    janium_campaign = db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == json_body['janium_campaign_id']).first()

    new_step = Janium_campaign_step(
        str(uuid4()),
        json_body['janium_campaign_id'],
        1 if 'email' not in json_body['janium_campaign_step_type'] else 2 if json_body['janium_campaign_step_type'] == 'email' else 4,
        json_body['janium_campaign_step_delay'],
        json_body['janium_campaign_step_body'],
        None if 'email' not in json_body['janium_campaign_step_type'] else json_body['janium_campaign_step_subject'],
        janium_campaign.queue_start_time,
        janium_campaign.queue_end_time,
        user_id
    )
    db.session.add(new_step)
    db.session.commit()
    return jsonify({"message": "Janium campaign step created successfully"})

@mod_campaign.route('/ulinc_campaigns', methods=['GET'])
@jwt_required()
def get_ulinc_campaigns():
    """
    Required query params: None
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if janium_accounts := user.accounts:
        janium_account = janium_accounts[0].account # Users are only associated with one Janium Campaign

        ulinc_campaigns = []
        for ulinc_campaign in janium_account.ulinc_campaigns:
            ulinc_campaigns.append(
                {
                    "ulinc_campaign_id": ulinc_campaign.ulinc_campaign_id,
                    "ulinc_campaign_name": ulinc_campaign.ulinc_campaign_name,
                    "ulinc_is_active": ulinc_campaign.ulinc_is_active
                }
            )
        return jsonify(ulinc_campaigns)

@mod_campaign.route('/assign_ulinc_campaign', methods=['PUT'])
@jwt_required()
def assign_ulinc_campaign():
    """
    Required JSON keys: janium_campaign_id, ulinc_campaign_id
    """
    json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    ulinc_campaign = db.session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_campaign_id == json_body['ulinc_campaign_id']).first()

    ulinc_campaign.janium_campaign_id = json_body['janium_campaign_id']

    return jsonify({"message": "Ulinc campaign associated to Janium campaign successfully"})