import pytest
import json
from foundation_api.V1.sa_db.model import Email_config, Janium_campaign, Ulinc_config, User, Janium_campaign_step, Contact, Action, Contact_source, Ulinc_campaign
import json
from uuid import uuid4
from datetime import datetime, timedelta


def test_get_li_message_targets(test_app, auth, campaign, session):
    headers = {"Content-Type": "application/json", "X-Appengine-Cron": True}
    assert test_app.get('/api/v1/jobs/send_li_message', headers=headers).status_code == 200

    auth.signup()
    login_response = auth.login()
    token = login_response.get_json()['access_token']

    ### Setup ###
    # Create Janium Campaign #
    janium_campaign = Janium_campaign(
        str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, Email_config.unassigned_email_config_id, "Test Janium Campaign",
        None, False, False, "9999-12-31 18:00:00", "9999-12-31 21:00:00")
    session.add(janium_campaign)

    # Create Janium Campaign Steps #
    step1 = Janium_campaign_step(str(uuid4()), janium_campaign.janium_campaign_id, 1, 10, 'Test LI Body 1', None, "9999-12-31 18:00:00", "9999-12-31 21:00:00")
    step2 = Janium_campaign_step(str(uuid4()), janium_campaign.janium_campaign_id, 1, 20, 'Test LI Body 2', None, "9999-12-31 18:00:00", "9999-12-31 21:00:00")
    step3 = Janium_campaign_step(str(uuid4()), janium_campaign.janium_campaign_id, 1, 30, 'Test LI Body 3', None, "9999-12-31 18:00:00", "9999-12-31 21:00:00")
    session.add(step1)
    session.add(step2)
    session.add(step3)

    # Create Ulinc Campaign #
    ulinc_campaign = Ulinc_campaign(str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, janium_campaign.janium_campaign_id, 'Test Ulinc Campaign', True, '1', False, None)
    session.add(ulinc_campaign)

    # Create Contact Source #
    contact_source = Contact_source(str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, 1, {})
    session.add(contact_source)

    # Create contact #
    contact_info = {"ulinc": {"email": None, "phone": None, "title": "Founder/CEO", "company": "Collateral Growth", "website": None, "location": "Phoenix, Arizona, United States", "last_name": "Lovegrove", "first_name": "Keith", "li_profile_url": None, "li_salesnav_profile_url": "https://www.linkedin.com/sales/profile/ACwAAAIteQwB3TSq4bfE3pJlEV1EOIpHA4FInHo,G40h,NAME_SEARCH"}}
    contact = Contact(str(uuid4()), contact_source.contact_source_id, ulinc_campaign.ulinc_campaign_id, '1234', ulinc_campaign.ulinc_ulinc_campaign_id, contact_info)
    session.add(contact)
    session.commit()








    ### Scenario 1 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    targets = janium_campaign.get_li_message_targets()
    janium_campaign_step = session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == targets[0]['janium_campaign_step_id']).first()

    session.commit()
    assert len(janium_campaign.get_li_message_targets()) == 1 and janium_campaign_step.janium_campaign_step_body == 'Test LI Body 1'

    session.delete(cnxn_action)
    session.commit()



    ### Scenario 2 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action)

    targets = janium_campaign.get_li_message_targets()
    janium_campaign_step = session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == targets[0]['janium_campaign_step_id']).first()

    session.commit()
    assert len(janium_campaign.get_li_message_targets()) == 1 and janium_campaign_step.janium_campaign_step_body == 'Test LI Body 2'

    session.delete(cnxn_action)
    session.delete(msg_action)
    session.commit()



    ### Scenario 3 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    targets = janium_campaign.get_li_message_targets()
    janium_campaign_step = session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == targets[0]['janium_campaign_step_id']).first()

    session.commit()
    assert len(janium_campaign.get_li_message_targets()) == 1 and janium_campaign_step.janium_campaign_step_body == 'Test LI Body 3'

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.commit()



    ### Scenario 4 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action)

    response_action = Action(str(uuid4()), contact.contact_id, 2, (datetime.utcnow() - timedelta(days=40)) + timedelta(hours=1), None)
    session.add(response_action)

    session.commit()
    assert len(janium_campaign.get_li_message_targets()) == 0

    session.delete(cnxn_action)
    session.delete(msg_action)
    session.delete(response_action)
    session.commit()



    ### Scenario 5 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    response_action = Action(str(uuid4()), contact.contact_id, 2, (datetime.utcnow() - timedelta(days=30)) + timedelta(hours=1), None)
    session.add(response_action)

    session.commit()
    assert len(janium_campaign.get_li_message_targets()) == 0

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(response_action)
    session.commit()



    ### Scenario 6 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    msg_action3 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=20), None)
    session.add(msg_action3)

    response_action = Action(str(uuid4()), contact.contact_id, 2, (datetime.utcnow() - timedelta(days=20)) + timedelta(hours=1), None)
    session.add(response_action)

    session.commit()
    assert len(janium_campaign.get_li_message_targets()) == 0

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(msg_action3)
    session.delete(response_action)
    session.commit()



    ### Scenario 7 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action)

    response_action = Action(str(uuid4()), contact.contact_id, 2, (datetime.utcnow() - timedelta(days=40)) + timedelta(hours=1), None)
    session.add(response_action)

    continue_action = Action(str(uuid4()), contact.contact_id, 14, datetime.utcnow() - timedelta(days=36), None)
    session.add(continue_action)

    targets = janium_campaign.get_li_message_targets()
    janium_campaign_step = session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == targets[0]['janium_campaign_step_id']).first()

    session.commit()
    assert len(janium_campaign.get_li_message_targets()) == 1 and janium_campaign_step.janium_campaign_step_body == 'Test LI Body 2'

    session.delete(cnxn_action)
    session.delete(msg_action)
    session.delete(response_action)
    session.delete(continue_action)
    session.commit()



    ### Scenario 7 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    response_action = Action(str(uuid4()), contact.contact_id, 2, (datetime.utcnow() - timedelta(days=30)) + timedelta(hours=1), None)
    session.add(response_action)

    continue_action = Action(str(uuid4()), contact.contact_id, 14, datetime.utcnow() - timedelta(days=26), None)
    session.add(continue_action)

    targets = janium_campaign.get_li_message_targets()
    janium_campaign_step = session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_step_id == targets[0]['janium_campaign_step_id']).first()

    session.commit()
    assert len(janium_campaign.get_li_message_targets()) == 1 and janium_campaign_step.janium_campaign_step_body == 'Test LI Body 3'

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(response_action)
    session.delete(continue_action)
    session.commit()



    ### Scenario 8 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    msg_action3 = Action(str(uuid4()), contact.contact_id, 3, datetime.utcnow() - timedelta(days=20), None)
    session.add(msg_action3)

    session.commit()
    assert len(janium_campaign.get_li_message_targets()) == 0

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(msg_action3)
    session.commit()
