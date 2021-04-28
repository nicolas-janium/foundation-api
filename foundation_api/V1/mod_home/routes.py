from datetime import datetime, timedelta, timezone
from uuid import uuid4
import os

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from foundation_api import app, bcrypt, db, mail
from foundation_api.V1.mod_home.models import User, Account, Ulinc_config, Credentials, Cookie, Contact, Action, Janium_campaign, Ulinc_campaign
from foundation_api.V1.utils.ulinc import get_ulinc_client_info, get_ulinc_tasks_count

mod_home = Blueprint('home', __name__, url_prefix='/api/v1')

@mod_home.route('/ulinc_configs', methods=['GET'])
@jwt_required()
def get_ulinc_configs():
    """
    Required query params: None
    """
    # json_body = request.get_json(force=True)
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    if janium_accounts := user.accounts:
        janium_account_id = janium_accounts[0].account_id # Users are only associated with one Janium Campaign
        janium_account = db.session.query(Account).filter(Account.account_id == janium_account_id).first()

        ulinc_configs = []

        for ulinc_config in janium_account.ulinc_configs:
            summary_data = ulinc_config.get_summary_data()
            # print(summary_data)
            ulinc_configs.append(
                {
                    "ulinc_config_id": ulinc_config.ulinc_config_id,
                    "ulinc_li_email": ulinc_config.ulinc_li_email,
                    "ulinc_is_active": ulinc_config.ulinc_is_active,
                    "ulinc_tasks_in_queue": get_ulinc_tasks_count(ulinc_config.ulinc_client_id, ulinc_config.cookie),
                    "summary_data": summary_data
                }
            )

        return jsonify(ulinc_configs)
    return jsonify({"message": "No Janium Account for user"})

@mod_home.route('/ulinc_config', methods=['GET'])
@jwt_required()
def get_ulinc_config():
    """
    Required query params: ulinc_config_id
    """
    # return "hello"
    # json_body = request.get_json(force=True)
    ulinc_config_id = request.args.get('ulinc_config_id')
    user_id = get_jwt_identity()
    user = db.session.query(User).filter(User.user_id == user_id).first()

    ulinc_config = db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == ulinc_config_id).first()

    janium_campaigns = []
    for janium_campaign in ulinc_config.janium_campaigns:
        janium_contacts = janium_campaign.contacts
        contacts_count = janium_contacts.count()
        connections_count = 0
        replies_count = 0
        for contact in janium_contacts:
            connections_count += contact.actions.filter(Action.action_type_id == 1).count()
            replies_count += contact.actions.filter(Action.action_type_id.in_([2,6])).count()


        janium_campaigns.append(
            {
                "janium_campaign_id": janium_campaign.janium_campaign_id,
                "janium_campaign_name": janium_campaign.janium_campaign_name,
                "janium_campaign_type": "Messenger" if janium_campaign.is_messenger else "Connector",
                "janium_campaign_contacts": contacts_count,
                "janium_campaign_connected": connections_count,
                "janium_campaign_replied": replies_count
            }
        )
    if os.getenv('PROJECT_ID') == 'foundation-staging-305217':
        return jsonify(
            {
                "ulinc_config_id": ulinc_config.ulinc_config_id,
                "janium_campaigns": janium_campaigns,
                "new_connections": [
                    {
                        "company": "Insightly",
                        "connection_date": "Wed, 28 Apr 2021 16:21:16 GMT",
                        "full_name": "Libby Mayer",
                        "janium_campaign_id": "9085776a-8a5e-4943-bc3d-d40b39b08130",
                        "janium_campaign_name": "Test Campaign 1",
                        "li_profile_url": "https://www.linkedin.com/sales/profile/ACwAAAngxzsBaMSwSyxiYRC7kC9GBX74NnKlT00,o3ZF,NAME_SEARCH",
                        "location": "Denver, Colorado, United States",
                        "title": "Senior Account Executive, Growth Sales",
                        "ulinc_campaign_id": "4720c3c8-4fc4-405c-96dd-3ce73197d4b8",
                        "ulinc_campaign_name": "IT+ - 50-500 - CO"
                    }
                ],
                "new_messages": [
                    {
                        "company": "Insightly",
                        "full_name": "Libby Mayer",
                        "janium_campaign_id": "9085776a-8a5e-4943-bc3d-d40b39b08130",
                        "janium_campaign_name": "Test Campaign 1",
                        "li_profile_url": "https://www.linkedin.com/sales/profile/ACwAAAngxzsBaMSwSyxiYRC7kC9GBX74NnKlT00,o3ZF,NAME_SEARCH",
                        "location": "Denver, Colorado, United States",
                        "msg_timestamp": "Wed, 28 Apr 2021 10:22:28 GMT",
                        "title": "Senior Account Executive, Growth Sales",
                        "ulinc_campaign_id": "4720c3c8-4fc4-405c-96dd-3ce73197d4b8",
                        "ulinc_campaign_name": "IT+ - 50-500 - CO"
                    }
                ],
                "vm_tasks": [
                    {
                        "company": "Insightly",
                        "connection_date": "Wed, 28 Apr 2021 16:21:16 GMT",
                        "full_name": "Libby Mayer",
                        "janium_campaign_id": "9085776a-8a5e-4943-bc3d-d40b39b08130",
                        "janium_campaign_name": "Test Campaign 1",
                        "li_profile_url": "https://www.linkedin.com/sales/profile/ACwAAAngxzsBaMSwSyxiYRC7kC9GBX74NnKlT00,o3ZF,NAME_SEARCH",
                        "location": "Denver, Colorado, United States",
                        "phone": "555-5555",
                        "title": "Senior Account Executive, Growth Sales",
                        "ulinc_campaign_id": "4720c3c8-4fc4-405c-96dd-3ce73197d4b8",
                        "ulinc_campaign_name": "IT+ - 50-500 - CO"
                    }
                ]
            }
        )
    return jsonify(
        {
            "ulinc_config_id": ulinc_config.ulinc_config_id,
            "janium_campaigns": janium_campaigns,
            "new_connections": ulinc_config.get_dte_new_connections(),
            "new_messages": ulinc_config.get_dte_new_messages(),
            "vm_tasks": ulinc_config.get_dte_vm_tasks()
        }
    )
