import base64
import json
import os
import sys
import pytest

from alembic.command import upgrade, downgrade
from alembic.config import Config

from foundation_api import create_app
from foundation_api.V1.sa_db.model import Janium_campaign, db as _db
from foundation_api.V1.sa_db.model import Ulinc_config, Email_config


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, os.pardir))
sys.path.insert(0, PROJECT_DIR)

ALEMBIC_CONFIG = 'alembic.ini'

headers={
    'content-type': 'application/json'
}



@pytest.fixture(scope='session')
def app(request):
    """Session-wide test `Flask` application."""
    app = create_app(test_config=True)
    os.environ['FLASK_TESTING'] = "1"

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app

@pytest.fixture(scope='session')
def test_app(app):
    return app.test_client()

def apply_migrations(teardown=False):
    """Applies all alembic migrations."""
    config = Config(ALEMBIC_CONFIG)
    if not teardown:
        upgrade(config, 'head')
    else:
        downgrade(config, 'base')

@pytest.fixture(scope='session')
def db(app, request):
    """Session-wide test database."""
    def teardown():
        apply_migrations(teardown=True)
        # _db.drop_all()

    _db.app = app
    apply_migrations()

    request.addfinalizer(teardown)
    return _db


@pytest.fixture(scope='function')
def session(db, request):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)
    
    db.session = session

    def teardown():
        transaction.rollback()
        connection.close()
        session.remove()

    request.addfinalizer(teardown)
    return session
 




class AuthActions(object):
    def __init__(self, test_app):
        self._client = test_app
    
    def signup(self):
        json_body = {
            "username": "test@test.com",
            "password": "test123",
            "first_name": "Test",
            "last_name": "User",
            "title": "Test",
            "company": "Test",
            "time_zone_code": "US/Mountain"
        }
        return self._client.post('/api/v1/signup', headers=headers, data=json.dumps(json_body))
    
    def login(self, username='test@test.com', password='test123'):
        headers={
            'content-type': 'application/json',
            'Authorization': 'Basic {}'.format(base64.b64encode(str(username + ':' + password).encode('utf-8')).decode('utf-8'))
            # 'Authorization': 'Basic dGVzdEB0ZXN0LmNvbTp0ZXN0MTIz'
        }
        return self._client.post(
            '/api/v1/login',
            headers=headers
        )
@pytest.fixture
def auth(test_app):
    return AuthActions(test_app)


class CampaignActions(object):
    def __init__(self, test_app):
        self._client = test_app
    
    def create_janium_campaign(self, token, janium_campaign_name):
        json_body = {
            "ulinc_config_id": Ulinc_config.unassigned_ulinc_config_id,
            "email_config_id": Email_config.unassigned_email_config_id,
            "janium_campaign_name": janium_campaign_name,
            "janium_campaign_description": None,
            "is_messenger": False,
            "is_reply_in_email_thread": False,
            "queue_start_time": "9999-12-31 09:00:00",
            "queue_end_time": "9999-12-31 12:00:00"
        }
        headers['Authorization'] = "Bearer {}".format(token)
        return self._client.post('/api/v1/janium_campaign', headers=headers, data=json.dumps(json_body))
    
    def create_janium_campaign_step(self, token, janium_campaign_id, step_type_id, delay):
        json_body = {
            "janium_campaign_id": janium_campaign_id,
            "janium_campaign_step_type_id": step_type_id,
            "janium_campaign_step_delay": delay,
            "janium_campaign_step_body": "Test Body",
            "janium_campaign_step_subject": "Test Subject"
        }
        headers['Authorization'] = "Bearer {}".format(token)
        return self._client.post('/api/v1/janium_campaign_step', headers=headers, data=json.dumps(json_body))

@pytest.fixture
def campaign(test_app):
    return CampaignActions(test_app)

class ContactActions(object):
    def __init__(self, test_app):
        self._client = test_app
    
    def create_contact(self):
        pass


@pytest.fixture
def contact(test_app):
    return ContactActions(test_app)