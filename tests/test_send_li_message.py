import pytest
import json
from foundation_api.V1.sa_db.model import User
import json

def test_get_li_message_targets(test_app, auth, session):
    headers = {"Content-Type": "application/json", "X-Appengine-Cron": True}
    assert test_app.get('/api/v1/jobs/send_li_message', headers=headers).status_code == 200
    auth.signup()

    