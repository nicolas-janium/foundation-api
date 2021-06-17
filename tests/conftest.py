import base64
import json
import os
import sys
import pytest

from alembic.command import upgrade, downgrade
from alembic.config import Config

from foundation_api import create_app
from foundation_api.V1.sa_db.model import db as _db


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(TEST_DIR, os.pardir))
sys.path.insert(0, PROJECT_DIR)

# ALEMBIC_CONFIG = '{}/alembic.ini'.format(PROJECT_DIR)
ALEMBIC_CONFIG = 'alembic.ini'



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
        # apply_migrations(teardown=True)
        # _db.drop_all()
        pass

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
        headers={
            'content-type': 'application/json'
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
    def logout(self, token):
        headers={
            'content-type': 'application/json',
            'Authorization': 'Bearer {}'.format(token)
        }
        return self._client.post(
            '/api/v1/logout',
            headers=headers
        )

@pytest.fixture
def auth(test_app):
    return AuthActions(test_app)