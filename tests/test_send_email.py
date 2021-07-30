from foundation_api.V1.utils import ulinc
import pytest
import json
from foundation_api.V1.sa_db.model import Janium_campaign, Ulinc_config, User, Janium_campaign_step, Contact, Action, Contact_source, Ulinc_campaign, Email_config, Account
import json
from uuid import uuid4
from datetime import datetime, timedelta

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from sqlalchemy.orm.attributes import flag_modified

gc_tasks_client = tasks_v2.CloudTasksClient()
gc_tasks_parent = gc_tasks_client.queue_path('foundation-staging-305217', 'us-central1', queue='send_email')

def setup_campaign(session):
    ### Setup ###
    # Create Janium Campaign #
    janium_campaign = Janium_campaign(
        str(uuid4()), Ulinc_config.unassigned_ulinc_config_id, Email_config.unassigned_email_config_id, "Test Janium Campaign",
        None, False, False, "9999-12-31 01:00:00", "9999-12-31 23:00:00")
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
    return (janium_campaign, contact)


def test_get_email_targets(test_app, auth, session):
    headers = {"Content-Type": "application/json", "X-Appengine-Cron": True}
    assert test_app.get('/api/v1/jobs/send_email', headers=headers).status_code == 200

    auth.signup()
    login_response = auth.login()
    token = login_response.get_json()['access_token']

    ### Setup ###
    janium_campaign, contact = setup_campaign(session)


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


def test_send_email_job_function(test_app, auth, session):
    headers = {"Content-Type": "application/json", "X-Appengine-Cron": True}
    assert test_app.get('/api/v1/jobs/send_email', headers=headers).status_code == 200

    auth.signup()
    login_response = auth.login()
    token = login_response.get_json()['access_token']

    janium_account_json_res = auth.get_janium_account(token).get_json()
    janium_account = session.query(Account).filter(Account.account_id == janium_account_json_res['janium_account_id']).first()
    assert janium_account.is_sending_emails == False

    auth.setup_janium_account(token)
    assert janium_account.is_sending_emails == True

    janium_account.effective_end_date = janium_account.effective_end_date + timedelta(days=300)
    janium_account.payment_effective_end_date = janium_account.payment_effective_end_date + timedelta(days=300)
    flag_modified(janium_account, 'effective_end_date')
    flag_modified(janium_account, 'payment_effective_end_date')
    session.commit()

    janium_campaign, contact = setup_campaign(session)

    ### Scenario 1 ###
    cnxn_action = Action(str(uuid4()), contact.contact_id, 1, datetime.utcnow() - timedelta(days=50), None)
    session.add(cnxn_action)
    session.commit()

    send_email_job_json_res = test_app.get('/api/v1/jobs/send_email', headers=headers).get_json()
    print(send_email_job_json_res)

    session.delete(cnxn_action)
    session.commit()

    
