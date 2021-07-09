import pytest
import json
from foundation_api.V1.sa_db.model import Janium_campaign, Ulinc_config, User, Janium_campaign_step, Contact, Action, Contact_source, Ulinc_campaign, Email_config
import json
from uuid import uuid4
from datetime import datetime, timedelta


def test_get_email_targets(test_app, auth, campaign, session):
    headers = {"Content-Type": "application/json", "X-Appengine-Cron": True}
    assert test_app.get('/api/v1/jobs/send_email', headers=headers).status_code == 200

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
    step1 = Janium_campaign_step(str(uuid4()), janium_campaign.janium_campaign_id, 4, 10, 'Test Pre-connection Email Body 1', 'Test Pre-connection Subject 1', "9999-12-31 18:00:00", "9999-12-31 21:00:00")
    step2 = Janium_campaign_step(str(uuid4()), janium_campaign.janium_campaign_id, 4, 20, 'Test Pre-connection Email Body 2', 'Test Pre-connection Subject 2', "9999-12-31 18:00:00", "9999-12-31 21:00:00")
    step3 = Janium_campaign_step(str(uuid4()), janium_campaign.janium_campaign_id, 4, 30, 'Test Pre-connection Email Body 3', 'Test Pre-connection Subject 3', "9999-12-31 18:00:00", "9999-12-31 21:00:00")

    step4 = Janium_campaign_step(str(uuid4()), janium_campaign.janium_campaign_id, 2, 10, 'Test Regular Email Body 1', 'Test Regular Subject 1', "9999-12-31 18:00:00", "9999-12-31 21:00:00")
    step5 = Janium_campaign_step(str(uuid4()), janium_campaign.janium_campaign_id, 2, 20, 'Test Regular Email Body 2', 'Test Regular Subject 2', "9999-12-31 18:00:00", "9999-12-31 21:00:00")
    step6 = Janium_campaign_step(str(uuid4()), janium_campaign.janium_campaign_id, 2, 30, 'Test Regular Email Body 3', 'Test Regular Subject 3', "9999-12-31 18:00:00", "9999-12-31 21:00:00")
    session.add(step1)
    session.add(step2)
    session.add(step3)
    session.add(step4)
    session.add(step5)
    session.add(step6)

    # Create Ulinc Campaign #
    ulinc_campaign = Ulinc_campaign(str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, janium_campaign.janium_campaign_id, 'Test Ulinc Campaign', True, '1', False, None)
    session.add(ulinc_campaign)

    # Create Contact Source #
    contact_source = Contact_source(str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, 1, {})
    session.add(contact_source)

    # Create contact #
    contact_info = {"ulinc": {"email": "123@gmail.com", "phone": None, "title": "Founder/CEO", "company": "Collateral Growth", "website": None, "location": "Phoenix, Arizona, United States", "last_name": "Lovegrove", "first_name": "Keith", "li_profile_url": None, "li_salesnav_profile_url": "https://www.linkedin.com/sales/profile/ACwAAAIteQwB3TSq4bfE3pJlEV1EOIpHA4FInHo,G40h,NAME_SEARCH"}}
    contact = Contact(str(uuid4()), contact_source.contact_source_id, ulinc_campaign.ulinc_campaign_id, '1234', ulinc_campaign.ulinc_ulinc_campaign_id, contact_info)
    session.add(contact)
    session.commit()



    ### Scenario 1 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 1'

    session.delete(cnxn_action)
    session.commit()



    ### Scenario 2 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 2'

    session.delete(cnxn_action)
    session.delete(msg_action)
    session.commit()



    ### Scenario 3 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 3'

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.commit()



    ### Scenario 4 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    msg_action3 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=20), None)
    session.add(msg_action3)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 0

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(msg_action3)
    session.commit()



    ### Scenario 5 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action)

    res_action = Action(str(uuid4()), contact.contact_id, 6, (datetime.utcnow() - timedelta(days=40)) + timedelta(hours=1), None)
    session.add(res_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 0

    session.delete(cnxn_action)
    session.delete(msg_action)
    session.delete(res_action)
    session.commit()



    ### Scenario 6 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    res_action = Action(str(uuid4()), contact.contact_id, 6, (datetime.utcnow() - timedelta(days=30)) + timedelta(hours=1), None)
    session.add(res_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 0

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(res_action)
    session.commit()



    ### Scenario 7 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    msg_action3 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=20), None)
    session.add(msg_action3)

    res_action = Action(str(uuid4()), contact.contact_id, 6, (datetime.utcnow() - timedelta(days=20)) + timedelta(hours=1), None)
    session.add(res_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 0

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(msg_action3)
    session.delete(res_action)
    session.commit()



    ### Scenario 8 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action)

    res_action = Action(str(uuid4()), contact.contact_id, 6, (datetime.utcnow() - timedelta(days=40)) + timedelta(hours=1), None)
    session.add(res_action)

    con_action = Action(str(uuid4()), contact.contact_id, 14, (datetime.utcnow() - timedelta(days=40)) + timedelta(hours=2), None)
    session.add(con_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 2'

    session.delete(cnxn_action)
    session.delete(msg_action)
    session.delete(res_action)
    session.delete(con_action)
    session.commit()




    ### Scenario 9 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    res_action = Action(str(uuid4()), contact.contact_id, 6, (datetime.utcnow() - timedelta(days=30)) + timedelta(hours=1), None)
    session.add(res_action)

    con_action = Action(str(uuid4()), contact.contact_id, 14, (datetime.utcnow() - timedelta(days=30)) + timedelta(hours=2), None)
    session.add(con_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 3'

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(res_action)
    session.delete(con_action)
    session.commit()




    ### Scenario 10 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    msg_action3 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=20), None)
    session.add(msg_action3)

    res_action = Action(str(uuid4()), contact.contact_id, 6, (datetime.utcnow() - timedelta(days=20)) + timedelta(hours=1), None)
    session.add(res_action)

    con_action = Action(str(uuid4()), contact.contact_id, 14, (datetime.utcnow() - timedelta(days=20)) + timedelta(hours=2), None)
    session.add(con_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 0

    session.delete(cnxn_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(msg_action3)
    session.delete(res_action)
    session.delete(con_action)
    session.commit()



    ### Scenario 11 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Pre-connection Email Body 1'

    session.delete(req_action)
    session.commit()



    ### Scenario 12 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Pre-connection Email Body 2'

    session.delete(req_action)
    session.delete(msg_action1)
    session.commit()



    ### Scenario 13 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Pre-connection Email Body 3'

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.commit()



    ### Scenario 14 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    msg_action3 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=20), None)
    session.add(msg_action3)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 0

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(msg_action3)
    session.commit()



    ### Scenario 15 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    res_action = Action(str(uuid4()), contact.contact_id, 6, (datetime.utcnow() - timedelta(days=40)) + timedelta(hours=1), None)
    session.add(res_action)

    con_action = Action(str(uuid4()), contact.contact_id, 14, (datetime.utcnow() - timedelta(days=40)) + timedelta(hours=2), None)
    session.add(con_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Pre-connection Email Body 2'

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(res_action)
    session.delete(con_action)
    session.commit()



    ### Scenario 15 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    res_action = Action(str(uuid4()), contact.contact_id, 6, (datetime.utcnow() - timedelta(days=30)) + timedelta(hours=1), None)
    session.add(res_action)

    con_action = Action(str(uuid4()), contact.contact_id, 14, (datetime.utcnow() - timedelta(days=30)) + timedelta(hours=2), None)
    session.add(con_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Pre-connection Email Body 3'

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(res_action)
    session.delete(con_action)
    session.commit()



    ### Scenario 15 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    msg_action3 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=20), None)
    session.add(msg_action3)

    res_action = Action(str(uuid4()), contact.contact_id, 6, (datetime.utcnow() - timedelta(days=20)) + timedelta(hours=1), None)
    session.add(res_action)

    con_action = Action(str(uuid4()), contact.contact_id, 14, (datetime.utcnow() - timedelta(days=20)) + timedelta(hours=2), None)
    session.add(con_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 0

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(msg_action3)
    session.delete(res_action)
    session.delete(con_action)
    session.commit()



    ### Scenario 16 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, (datetime.utcnow() - timedelta(days=40)) + timedelta(hours=1), None)
    session.add(cnxn_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 1'

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(cnxn_action)
    session.commit()



    ### Scenario 17 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, (datetime.utcnow() - timedelta(days=30)) + timedelta(hours=1), None)
    session.add(cnxn_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 1'

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(cnxn_action)
    session.commit()



    ### Scenario 18 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    msg_action3 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=20), None)
    session.add(msg_action3)

    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, (datetime.utcnow() - timedelta(days=20)) + timedelta(hours=1), None)
    session.add(cnxn_action)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 1'

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(msg_action3)
    session.delete(cnxn_action)
    session.commit()



    ### Scenario 19 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action1)

    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, (datetime.utcnow() - timedelta(days=40)) + timedelta(hours=1), None)
    session.add(cnxn_action)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action2)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 2'

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(cnxn_action)
    session.commit()




    ### Scenario 20 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=60), None)
    session.add(req_action)

    msg_action1 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=50), None)
    session.add(msg_action1)

    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, (datetime.utcnow() - timedelta(days=50)) + timedelta(hours=1), None)
    session.add(cnxn_action)

    msg_action2 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=40), None)
    session.add(msg_action2)

    msg_action3 = Action(str(uuid4()), contact.contact_id, 4, datetime.utcnow() - timedelta(days=30), None)
    session.add(msg_action3)

    session.commit()
    assert len(janium_campaign.get_email_targets()) == 1 and janium_campaign.get_email_targets()[0]['email_body'] == 'Test Regular Email Body 3'

    session.delete(req_action)
    session.delete(msg_action1)
    session.delete(msg_action2)
    session.delete(msg_action3)
    session.delete(cnxn_action)
    session.commit()














    # janium_campaign_name = 'Test Janium Campaign'
    # existing_janium_campaigns = session.query(Janium_campaign).count()
    # campaign.create_janium_campaign(token, janium_campaign_name)
    # assert session.query(Janium_campaign).count() == existing_janium_campaigns + 1

    # janium_campaign = session.query(Janium_campaign).filter(Janium_campaign.janium_campaign_name == janium_campaign_name).first()
    # existing_janium_campaign_steps = session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_id == janium_campaign.janium_campaign_id).count()
    # campaign.create_janium_campaign_step(token, janium_campaign.janium_campaign_id, step_type_id=2, delay=1)
    # campaign.create_janium_campaign_step(token, janium_campaign.janium_campaign_id, step_type_id=2, delay=3)
    # campaign.create_janium_campaign_step(token, janium_campaign.janium_campaign_id, step_type_id=4, delay=1)
    # campaign.create_janium_campaign_step(token, janium_campaign.janium_campaign_id, step_type_id=4, delay=3)
    # assert session.query(Janium_campaign_step).filter(Janium_campaign_step.janium_campaign_id == janium_campaign.janium_campaign_id).count() == existing_janium_campaign_steps + 4

    # ### Setup ###
    # # Create Ulinc Campaign #
    # ulinc_campaign = Ulinc_campaign(str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, janium_campaign.janium_campaign_id, 'Test Ulinc Campaign', True, '1', False, None)
    # session.add(ulinc_campaign)

    # # Create Contact Source #
    # contact_source = Contact_source(str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, 1, {})
    # session.add(contact_source)

    # # Create contact #
    # contact_info = {"ulinc": {"email": "123@gmail.com", "phone": None, "title": "Founder/CEO", "company": "Collateral Growth", "website": None, "location": "Phoenix, Arizona, United States", "last_name": "Lovegrove", "first_name": "Keith", "li_profile_url": None, "li_salesnav_profile_url": "https://www.linkedin.com/sales/profile/ACwAAAIteQwB3TSq4bfE3pJlEV1EOIpHA4FInHo,G40h,NAME_SEARCH"}}
    # new_contact = Contact(str(uuid4()), contact_source.contact_source_id, ulinc_campaign.ulinc_campaign_id, '1234', ulinc_campaign.ulinc_ulinc_campaign_id, contact_info)
    # session.add(new_contact)


    # ### Test Pre Connection Email actions ###
    # # Create Connection Request Action #
    # cnx_req_action = Action(str(uuid4()), new_contact.contact_id, 19, datetime.utcnow() - timedelta(days=10), None)
    # session.add(cnx_req_action)
    # session.commit()

    # assert len(janium_campaign.get_email_targets()) == 1


    # # Test Continue Action
    # response_action = Action(str(uuid4()), new_contact.contact_id, 6, datetime.utcnow() - timedelta(days=9), None)
    # session.add(response_action)
    # session.commit()

    # assert len(janium_campaign.get_email_targets()) == 0

    # continue_action = Action(str(uuid4()), new_contact.contact_id, 14, (datetime.utcnow() - timedelta(days=9)) + timedelta(hours=1), None)
    # session.add(continue_action)
    # session.commit()

    # assert len(janium_campaign.get_email_targets()) == 1

    # session.delete(response_action)
    # session.delete(continue_action)


    # # Test Next Pre connection email action
    # message_action = Action(str(uuid4()), new_contact.contact_id, 4, datetime.utcnow() - timedelta(days=9), None)
    # session.add(message_action)
    # session.commit()

    # assert len(janium_campaign.get_email_targets()) == 1

    # message_action = Action(str(uuid4()), new_contact.contact_id, 4, datetime.utcnow() - timedelta(days=7), None)
    # session.add(message_action)
    # session.commit()



    # ### Test First Step/email action ###
    # # Create Connection Action #
    # cnx_action = Action(str(uuid4()), new_contact.contact_id, 1, datetime.utcnow() - timedelta(days=5), None)
    # session.add(cnx_action)
    # session.commit()

    # assert len(janium_campaign.get_email_targets()) == 1


    # ### Test Continue Campaign Action ###
    # # Create Response Action #
    # response_action = Action(str(uuid4()), new_contact.contact_id, 6, datetime.utcnow() - timedelta(days=4), None)
    # session.add(response_action)
    # session.commit()

    # assert len(janium_campaign.get_email_targets()) == 0

    # # Create Continue Campaign Action #
    # continue_action = Action(str(uuid4()), new_contact.contact_id, 14, (datetime.utcnow() - timedelta(days=4)) + timedelta(hours=1), None)
    # session.add(continue_action)
    # session.commit()

    # assert len(janium_campaign.get_email_targets()) == 1

    # # Clean Up #
    # session.delete(response_action)
    # session.delete(continue_action)


    # ### Test after sent message action recorded ###
    # # Create Sent Message Action #
    # message_action = Action(str(uuid4()), new_contact.contact_id, 4, datetime.utcnow() - timedelta(days=4), None)
    # session.add(message_action)
    # session.commit()

    # assert len(janium_campaign.get_email_targets()) == 1

    # message_action = Action(str(uuid4()), new_contact.contact_id, 4, datetime.utcnow() - timedelta(days=2), None)
    # session.add(message_action)
    # session.commit()

    # assert len(janium_campaign.get_email_targets()) == 0


    