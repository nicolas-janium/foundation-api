from datetime import datetime, timedelta
from uuid import uuid4

from flask import Blueprint, json, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm.attributes import flag_modified

from foundation_api import check_json_header
from foundation_api.V1.sa_db.model import db
from foundation_api.V1.sa_db.model import Janium_campaign, Ulinc_campaign, Janium_campaign_step, Ulinc_config, Account, Contact
from foundation_api.V1.utils.refresh_ulinc_data import refresh_ulinc_campaigns


mod_campaign = Blueprint('campaign', __name__, url_prefix='/api/v1')


@mod_campaign.route('/janium_campaigns', methods=['GET'])
@jwt_required()
def get_janium_campaigns():
    """
    Required query params: ulinc_config_id
    """
    if ulinc_config_id := request.args.get('ulinc_config_id'):
        if ulinc_config := db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == ulinc_config_id).first():
            return jsonify(ulinc_config.get_janium_campaigns())
        return make_response(jsonify({"message": "Unknown ulinc_config_id value"}), 400)
    return make_response(jsonify({"message": "Missing ulinc_config_id param"}), 400)

@mod_campaign.route('/janium_campaign', methods=['GET'])
@jwt_required()
def get_janium_campaign():
    """
    Required query params: janium_campaign_id
    """
    user_id = get_jwt_identity()
    if janium_campaign_id := request.args.get('janium_campaign_id'):
        if janium_campaign := db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == janium_campaign_id).first():
            janium_account = db.session.query(Account).filter(Account.user_id == user_id).first()

            ulinc_config = janium_campaign.janium_campaign_ulinc_config

            return jsonify(
                {
                    "janium_campaign_id": janium_campaign_id,
                    "janium_campaign_name": janium_campaign.janium_campaign_name,
                    "janium_campaign_description": janium_campaign.janium_campaign_description,
                    "janium_campaign_is_active": janium_campaign.is_active(),
                    "email_config_id": janium_campaign.email_config_id,
                    "email_config_from_full_name": janium_campaign.email_config.from_full_name,
                    "email_config_from_address": janium_campaign.email_config.from_address,
                    "queue_start_time": janium_account.convert_utc_to_account_local(janium_campaign.queue_start_time),
                    "queue_end_time": janium_account.convert_utc_to_account_local(janium_campaign.queue_end_time),
                    "child_ulinc_campaigns": janium_campaign.get_ulinc_campaigns(),
                    "total_ulinc_campaigns": ulinc_config.get_ulinc_campaigns(),
                    "janium_campaign_steps": janium_campaign.get_steps(),
                    "contact_list": janium_campaign.get_contacts()
                }
            )
        return make_response(jsonify({"message": "Unknown janium_campaign_id value"}), 400)
    return make_response(jsonify({"message": "Missing janium_campaign_id param"}), 400)

@mod_campaign.route('/janium_campaign', methods=['POST'])
@jwt_required()
@check_json_header
def create_janium_campaign():
    """
    Required JSON keys: ulinc_config_id, email_config_id, janium_campaign_name,
    janium_campaign_description, is_messenger, is_reply_in_email_thread, queue_start_hour (int), queue_start_minute (int), queue_end_hour (int), queue_end_minute (int)
    """
    user_id = get_jwt_identity()
    if json_body := request.get_json():
        if db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_name == json_body['janium_campaign_name']).first():
            return make_response(jsonify({"message": "A Janium campaign with that name already exists"}), 409)
        
        janium_account = db.session.query(Account).filter(Account.user_id == user_id).first()

        janium_campaign = Janium_campaign(
            str(uuid4()),
            json_body['ulinc_config_id'],
            json_body['email_config_id'],
            json_body['janium_campaign_name'],
            json_body['janium_campaign_description'],
            json_body['is_messenger'],
            json_body['is_reply_in_email_thread'],
            janium_account.create_campaign_queue_time(json_body['queue_start_hour'], json_body['queue_start_minute']),
            janium_account.create_campaign_queue_time(json_body['queue_end_hour'], json_body['queue_end_minute'])
        )
        db.session.add(janium_campaign)
        db.session.commit()
        return jsonify({"message": "success"})
    return make_response(jsonify({"message": "Missing JSON body"}), 400)

@mod_campaign.route('/janium_campaign', methods=['PUT'])
@jwt_required()
@check_json_header
def update_janium_campaign():
    """
    Required JSON keys: janium_campaign_id, email_config_id, janium_campaign_name,
    janium_campaign_description, queue_start_hour, queue_start_minute, queue_end_hour, queue_end_minute, is_active, is_reply_in_email_thread
    """
    user_id = get_jwt_identity()
    if json_body := request.get_json():
        if janium_campaign := db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == json_body['janium_campaign_id']).first():
            janium_account = db.session.query(Account).filter(Account.user_id == user_id).first()

            janium_campaign.janium_campaign_name = json_body['janium_campaign_name']
            janium_campaign.janium_campaign_description = json_body['janium_campaign_description']
            janium_campaign.email_config_id = json_body['email_config_id']
            janium_campaign.is_reply_in_email_thread = json_body['is_reply_in_email_thread']
            janium_campaign.queue_start_time = janium_account.create_campaign_queue_time(json_body['queue_start_hour'], json_body['queue_start_minute'])
            janium_campaign.queue_end_time = janium_account.create_campaign_queue_time(json_body['queue_end_hour'], json_body['queue_end_minute'])
            janium_campaign.effective_start_date = datetime.utcnow()
            janium_campaign.effective_end_date = datetime.utcnow() + timedelta(days=365000) if json_body['is_active'] else datetime.utcnow()
            db.session.commit()
            return jsonify({"message": "success"})
        return make_response(jsonify({"message": "Unknown janium_campaign_id value"}), 400)
    return make_response(jsonify({"message": "JSON body is missing"}), 400)

# @mod_campaign.route('/janium_campaign_step', methods=['POST'])
# @jwt_required()
# @check_json_header
# def create_janium_campaign_step():
#     """
#     Required JSON keys: janium_campaign_id, janium_campaign_step_type_id (li_message: 1, email: 2, pre_connection_email: 4, text: 3), janium_campaign_step_delay,
#     janium_campaign_step_body, janium_campaign_step_subject (if type == email or type == pre_connection_email), 
#     """
#     user_id = get_jwt_identity()
#     if json_body := request.get_json():
#         if existing_step := db.session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_id == json_body['janium_campaign_id']).filter(Janium_campaign_step.janium_campaign_step_delay == json_body['janium_campaign_step_delay']).filter(Janium_campaign_step.janium_campaign_step_type_id == json_body['janium_campaign_step_type_id']).first():
#             return make_response(jsonify({"message": "Duplicate step (Delay and type)"}), 400)
#         if json_body['janium_campaign_step_type_id'] not in [1,2,3,4]:
#             return make_response(jsonify({"message": "Invalid janium_campaign_step_type_id value"}), 400)
#         else:
#             if janium_campaign := db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == json_body['janium_campaign_id']).first():
#                 new_step = Janium_campaign_step(
#                     str(uuid4()),
#                     json_body['janium_campaign_id'],
#                     json_body['janium_campaign_step_type_id'],
#                     json_body['janium_campaign_step_delay'],
#                     json_body['janium_campaign_step_body'],
#                     json_body['janium_campaign_step_subject'] if json_body['janium_campaign_step_type_id'] in [2,4] else None,
#                     janium_campaign.queue_start_time,
#                     janium_campaign.queue_end_time
#                 )
#                 db.session.add(new_step)
#                 db.session.commit()
#                 return jsonify({"message": "success"})
#             return make_response(jsonify({"message": "Unknown janium_campaign_id value"}), 400)
#     return make_response(jsonify({"message": "JSON body is missing"}), 400)

# @mod_campaign.route('/janium_campaign_step', methods=['PUT'])
# @jwt_required()
# @check_json_header
# def update_janium_campaign_step():
#     """
#     Required JSON keys: janium_campaign_step_id, janium_campaign_step_delay, janium_campaign_step_body,
#                         janium_campaign_step_subject
#     """
#     user_id = get_jwt_identity()
#     if json_body := request.get_json():
#         if janium_campaign_step := db.session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == json_body['janium_campaign_step_id']).first():
#             janium_campaign_step.janium_campaign_step_delay = json_body['janium_campaign_step_delay']
#             janium_campaign_step.janium_campaign_step_body = json_body['janium_campaign_step_body']
#             janium_campaign_step.janium_campaign_step_subject = json_body['janium_campaign_step_subject']
#             db.session.commit()
#             return jsonify({"message": "success"})
#         return make_response(jsonify({"message": "Unknown janium_campaign_step_id value"}), 400)
#     return make_response(jsonify({"message": "JSON body is missing"}), 400)

@mod_campaign.route('/janium_campaign_steps', methods=['POST'])
@jwt_required()
@check_json_header
def create_janium_campaign_steps():
    """
    Required JSON keys: [
        janium_campaign_id,
        janium_campaign_step_type_id (li_message: 1, email: 2, pre_connection_email: 4, text: 3),
        janium_campaign_step_delay,
        janium_campaign_step_body,
        janium_campaign_step_subject (if type == email or type == pre_connection_email)
    ]
    """
    user_id = get_jwt_identity()
    if json_body := request.get_json():
        if janium_campaign := db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == json_body[0]['janium_campaign_id']).first():
            for step in json_body:
                if existing_step := db.session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_id == step['janium_campaign_id']).filter(Janium_campaign_step.janium_campaign_step_delay == step['janium_campaign_step_delay']).filter(Janium_campaign_step.janium_campaign_step_type_id == step['janium_campaign_step_type_id']).first():
                    continue
                if step['janium_campaign_step_type_id'] not in [1,2,3,4]:
                    continue
                else:
                    new_step = Janium_campaign_step(
                        str(uuid4()),
                        step['janium_campaign_id'],
                        step['janium_campaign_step_type_id'],
                        step['janium_campaign_step_delay'],
                        step['janium_campaign_step_body'],
                        step['janium_campaign_step_subject'] if step['janium_campaign_step_type_id'] in [2,4] else None,
                        janium_campaign.queue_start_time,
                        janium_campaign.queue_end_time
                    )
                    db.session.add(new_step)
                db.session.commit()
                return make_response(jsonify({"message": "success"}), 200)
            return make_response(jsonify({"message": "success"}), 200)
        return make_response(jsonify({"message": "Unknown janium_campaign_step_id value"}), 400)
    return make_response(jsonify({"message": "JSON body is missing"}), 400)

@mod_campaign.route('/janium_campaign_steps', methods=['PUT'])
@jwt_required()
@check_json_header
def update_janium_campaign_steps():
    """
    Required JSON keys: [
        janium_campaign_step_id,
        janium_campaign_step_delay,
        janium_campaign_step_body,
        janium_campaign_step_subject
    ]
    """
    user_id = get_jwt_identity()
    if json_body := request.get_json():
        for step in json_body:
            if janium_campaign_step := db.session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == step['janium_campaign_step_id']).first():
                janium_campaign_step.janium_campaign_step_delay = step['janium_campaign_step_delay']
                janium_campaign_step.janium_campaign_step_body = step['janium_campaign_step_body']
                janium_campaign_step.janium_campaign_step_subject = step['janium_campaign_step_subject']
                db.session.commit()
        return jsonify({"message": "success"})
    return make_response(jsonify({"message": "JSON body is missing"}), 400)

@mod_campaign.route('/ulinc_campaigns', methods=['GET'])
@jwt_required()
def get_ulinc_campaigns():
    """
    Required query params: Ulinc_config_id
    """
    if ulinc_config_id := request.args.get('ulinc_config_id'):
        if ulinc_config := db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == ulinc_config_id).first():
            return jsonify(ulinc_config.get_ulinc_campaigns())
        return make_response(jsonify({"message": "Unknown ulinc_config_id value"}), 400)
    return make_response(jsonify({"message": "Missing ulinc_config_id param"}), 400)

@mod_campaign.route('/ulinc_campaign', methods=['GET'])
@jwt_required()
def get_ulinc_campaign():
    """
    Required query params: None
    """
    user_id = get_jwt_identity()
    if ulinc_campaign_id := request.args.get('ulinc_campaign_id'):
        if ulinc_campaign := db.session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_campaign_id == ulinc_campaign_id).first():
            return jsonify(
                {
                    "ulinc_campaign_id": ulinc_campaign.ulinc_campaign_id,
                    "ulinc_campaign_name": ulinc_campaign.ulinc_campaign_name,
                    "total_contacts": ulinc_campaign.get_total_num_contacts(),
                    "total_connections": ulinc_campaign.get_total_num_connections(),
                    "total_responses": ulinc_campaign.get_total_num_responses()
                }
            )
        return make_response(jsonify({"message": "Unknown ulinc_campaign_id value"}), 400)
    return make_response(jsonify({"message": "Missing ulinc_campaign_id param"}), 400)

@mod_campaign.route('/refresh_ulinc_campaigns', methods=['GET'])
@jwt_required()
def refresh_ulinc_campaigns_endpoint():
    """
    Required query params: ulinc_config_id
    """ 
    user_id = get_jwt_identity()
    if ulinc_config_id := request.args.get('ulinc_config_id'):
        if ulinc_config := db.session.query(Ulinc_config).filter(Ulinc_config.ulinc_config_id == ulinc_config_id).first():
            if refresh_ulinc_campaigns(ulinc_config):
                return jsonify({"message": "success"})
            else:
                return make_response(jsonify({"message": "Internal server error"}), 500)
        return make_response(jsonify({"message": "Unknown ulinc_config_id value"}), 400)
    return make_response(jsonify({"message": "Missing ulinc_config_id param"}), 400)



@mod_campaign.route('/ulinc_campaign', methods=['PUT'])
@jwt_required()
@check_json_header
def update_ulinc_campaign():
    """
    Required JSON keys: janium_campaign_id, ulinc_campaign_id
    """

    user_id = get_jwt_identity()
    if json_body := request.get_json():
        return_list = []
        for ulinc_campaign_id in json_body["ulinc_campaign_ids"]:
            if ulinc_campaign := db.session.query(Ulinc_campaign).filter(Ulinc_campaign.ulinc_campaign_id == ulinc_campaign_id).first():
                if janium_campaign := db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == json_body['janium_campaign_id']).first():
                    ulinc_campaign.janium_campaign_id = janium_campaign.janium_campaign_id
                    ulinc_config = ulinc_campaign.ulinc_config
                    db.session.commit()
                    return_list.append(
                        {
                            "ulinc_campaign_id": ulinc_campaign.ulinc_campaign_id,
                            "ulinc_campaign_name": ulinc_campaign.ulinc_campaign_name,
                            "ulinc_ulinc_campaign_id": ulinc_campaign.ulinc_ulinc_campaign_id,
                            "ulinc_campaign_is_active": ulinc_campaign.ulinc_is_active,
                            "parent_janium_campaign_id": ulinc_campaign.parent_janium_campaign.janium_campaign_id,
                            "parent_janium_campaign_name": ulinc_campaign.parent_janium_campaign.janium_campaign_name
                        }
                    )
        return jsonify(return_list)
    return make_response(jsonify({"message": "JSON body is missing"}), 400)


@mod_campaign.route('/janium_campaign_contacts', methods=['GET'])
@jwt_required()
def get_janium_campaign_contacts():
    """
    Required query params: janium_campaign_id, page
    """
    user_id = get_jwt_identity()
    if janium_campaign_id := request.args.get('janium_campaign_id'):
        if janium_campaign := db.session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_id == janium_campaign_id).first():
            if page_number := int(request.args.get('page')):
                return_list = []
                pagination_item = db.session.query(Contact, Ulinc_campaign).filter(Contact.ulinc_campaign_id == Ulinc_campaign.ulinc_campaign_id).filter(Ulinc_campaign.janium_campaign_id == janium_campaign_id).order_by(Contact.contact_info['ulinc']['first_name']).paginate(page=page_number, per_page=25, error_out=True)
                for query_item in pagination_item.items:
                    query_item_dict = query_item._asdict()
                    contact = query_item_dict['Contact']
                    contact_info = contact.contact_info['ulinc']
                    return_list.append(
                        {
                            "contact_id": contact.contact_id,
                            "first_name": contact_info['first_name'],
                            "last_name": contact_info['last_name'],
                            "title": contact_info['title'],
                            "company": contact_info['company'],
                            "location": contact_info['location'],
                            "email": contact_info['email'],
                            "phone": contact_info['phone'],
                            "li_profile_url": contact_info['li_profile_url'] if contact_info['li_profile_url'] else contact_info['li_salesnav_profile_url']
                        }
                    )
                return_list = sorted(return_list, key = lambda item: item['first_name'])
                return jsonify(
                    {
                        "contacts": return_list,
                        "pagination_info": {
                            "has_prev_page": pagination_item.has_prev,
                            "has_next_page": pagination_item.has_next,
                            "current_page": page_number,
                            "total_pages": pagination_item.pages,
                            "items_per_page": pagination_item.per_page
                        }
                    }
                )
            return make_response(jsonify({"message": "Missing page param"}), 400)
        return make_response(jsonify({"message": "Unknown janium_campaign_id value"}), 400)
    return make_response(jsonify({"message": "Missing janium_campaign_id param"}), 400)

@mod_campaign.route('/modify_contacts', methods=['POST'])
@jwt_required()
def modify_janium_campaign_contacts():
    """
    Required JSON keys: list of JSON contact objects
    """
    user_id = get_jwt_identity()
    if json_body := request.get_json():
        for contact_item in json_body:
            if contact := db.session.query(Contact).filter(Contact.contact_id == contact_item['contact_id']).first():
                contact_info = contact.contact_info
                contact_info['ulinc']['modified_first_name'] = contact_item['modified_first_name']
                contact_info['ulinc']['modified_company'] = contact_item['modified_company']
                contact_info['ulinc']['modified_location'] = contact_item['modified_location']
                contact.contact_info = contact_info
                flag_modified(contact, 'contact_info')
                db.session.commit()
            else:
                return make_response(jsonify({"message": "Unknown contact_id value in JSON body"}), 400)
        return jsonify({"message": "success"})
    return make_response(jsonify({"message": "JSON body is missing"}), 400)

    