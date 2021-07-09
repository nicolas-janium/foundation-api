import pytest
import json
from foundation_api.V1.sa_db.model import Janium_campaign, Ulinc_config, User, Janium_campaign_step, Contact, Action, Contact_source, Ulinc_campaign, Email_config
import json
from uuid import uuid4
from datetime import datetime, timedelta


def test_get_data_enrichment_targets(test_app, auth, campaign, session):
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
    contact_info = {"ulinc": {"email": None, "phone": None, "title": "Founder/CEO", "company": "Collateral Growth", "website": None, "location": "Phoenix, Arizona, United States", "last_name": "Lovegrove", "first_name": "Keith", "li_profile_url": "https://www.linkedin.com/in/keith-lovegrove/", "li_salesnav_profile_url": "https://www.linkedin.com/sales/profile/ACwAAAIteQwB3TSq4bfE3pJlEV1EOIpHA4FInHo,G40h,NAME_SEARCH"}}
    contact = Contact(str(uuid4()), contact_source.contact_source_id, ulinc_campaign.ulinc_campaign_id, '1234', ulinc_campaign.ulinc_ulinc_campaign_id, contact_info)
    session.add(contact)
    session.commit()

    ### Scenario 1 ###
    req_action = Action(str(uuid4()), contact.contact_id, 19, datetime.utcnow() - timedelta(days=50), None)
    session.add(req_action)

    session.commit()
    assert len(janium_campaign.get_data_enrichment_targets()) == 1

    session.delete(req_action)
    session.commit()