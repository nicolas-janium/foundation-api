import pytest
import json
from foundation_api.V1.sa_db.model import Janium_campaign, Ulinc_config, User, Janium_campaign_step, Contact, Action, Contact_source, Ulinc_campaign
import json
from uuid import uuid4
from datetime import datetime, timedelta


def test_get_email_targets(test_app, auth, campaign, session):
    headers = {"Content-Type": "application/json", "X-Appengine-Cron": True}
    assert test_app.get('/api/v1/jobs/send_email', headers=headers).status_code == 200

    auth.signup()
    login_response = auth.login()
    token = login_response.get_json()['access_token']

    janium_campaign_name = 'Test Janium Campaign'
    existing_janium_campaigns = session.query(Janium_campaign).count()
    campaign.create_janium_campaign(token, janium_campaign_name)
    assert session.query(Janium_campaign).count() == existing_janium_campaigns + 1

    janium_campaign = session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_name == janium_campaign_name).first()
    existing_janium_campaign_steps = session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_id == janium_campaign.janium_campaign_id).count()
    campaign.create_janium_campaign_step(token, janium_campaign.janium_campaign_id, step_type_id=2, delay=1)
    campaign.create_janium_campaign_step(token, janium_campaign.janium_campaign_id, step_type_id=2, delay=3)
    campaign.create_janium_campaign_step(token, janium_campaign.janium_campaign_id, step_type_id=4, delay=1)
    campaign.create_janium_campaign_step(token, janium_campaign.janium_campaign_id, step_type_id=4, delay=3)
    assert session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_id == janium_campaign.janium_campaign_id).count() == existing_janium_campaign_steps + 4

    ### Setup ###
    # Create Ulinc Campaign #
    ulinc_campaign = Ulinc_campaign(str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, janium_campaign.janium_campaign_id, 'Test Ulinc Campaign', True, '1', False, None)
    session.add(ulinc_campaign)

    # Create Contact Source #
    contact_source = Contact_source(str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, 1, {})
    session.add(contact_source)

    # Create contact #
    contact_info = {"ulinc": {"email": "123@gmail.com", "phone": None, "title": "Founder/CEO", "company": "Collateral Growth", "website": None, "location": "Phoenix, Arizona, United States", "last_name": "Lovegrove", "first_name": "Keith", "li_profile_url": None, "li_salesnav_profile_url": "https://www.linkedin.com/sales/profile/ACwAAAIteQwB3TSq4bfE3pJlEV1EOIpHA4FInHo,G40h,NAME_SEARCH"}}
    new_contact = Contact(str(uuid4()), contact_source.contact_source_id, ulinc_campaign.ulinc_campaign_id, '1234', ulinc_campaign.ulinc_ulinc_campaign_id, contact_info)
    session.add(new_contact)


    ### Test Pre Connection Email actions ###
    # Create Connection Request Action #
    cnx_req_action = Action(str(uuid4()), new_contact.contact_id, 19, datetime.utcnow() - timedelta(days=10), None)
    session.add(cnx_req_action)
    session.commit()

    assert len(janium_campaign.get_email_targets()) == 1


    # Test Continue Action
    response_action = Action(str(uuid4()), new_contact.contact_id, 6, datetime.utcnow() - timedelta(days=9), None)
    session.add(response_action)
    session.commit()

    assert len(janium_campaign.get_email_targets()) == 0

    continue_action = Action(str(uuid4()), new_contact.contact_id, 14, (datetime.utcnow() - timedelta(days=9)) + timedelta(hours=1), None)
    session.add(continue_action)
    session.commit()

    assert len(janium_campaign.get_email_targets()) == 1

    session.delete(response_action)
    session.delete(continue_action)


    # Test Next Pre connection email action
    message_action = Action(str(uuid4()), new_contact.contact_id, 4, datetime.utcnow() - timedelta(days=9), None)
    session.add(message_action)
    session.commit()

    assert len(janium_campaign.get_email_targets()) == 1

    message_action = Action(str(uuid4()), new_contact.contact_id, 4, datetime.utcnow() - timedelta(days=7), None)
    session.add(message_action)
    session.commit()



    ### Test First Step/email action ###
    # Create Connection Action #
    cnx_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow() - timedelta(days=5), None)
    session.add(cnx_action)
    session.commit()

    assert len(janium_campaign.get_email_targets()) == 1


    ### Test Continue Campaign Action ###
    # Create Response Action #
    response_action = Action(str(uuid4()), new_contact.contact_id, 6, datetime.utcnow() - timedelta(days=4), None)
    session.add(response_action)
    session.commit()

    assert len(janium_campaign.get_email_targets()) == 0

    # Create Continue Campaign Action #
    continue_action = Action(str(uuid4()), new_contact.contact_id, 14, (datetime.utcnow() - timedelta(days=4)) + timedelta(hours=1), None)
    session.add(continue_action)
    session.commit()

    assert len(janium_campaign.get_email_targets()) == 1

    # Clean Up #
    session.delete(response_action)
    session.delete(continue_action)


    ### Test after sent message action recorded ###
    # Create Sent Message Action #
    message_action = Action(str(uuid4()), new_contact.contact_id, 4, datetime.utcnow() - timedelta(days=4), None)
    session.add(message_action)
    session.commit()

    assert len(janium_campaign.get_email_targets()) == 1

    message_action = Action(str(uuid4()), new_contact.contact_id, 4, datetime.utcnow() - timedelta(days=2), None)
    session.add(message_action)
    session.commit()

    assert len(janium_campaign.get_email_targets()) == 0


    