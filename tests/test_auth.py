# import pytest
# import json
# from foundation_api.V1.sa_db.model import User
# import json

# def test_signup(test_app, auth, session):
#     assert test_app.post('/api/v1/signup', headers={"Content-Type": "application/json"}, data=json.dumps({})).status_code == 200
#     existing_count = session.query(User).count()

#     response = auth.signup()
#     assert response.status_code == 200
#     assert session.query(User).count() == existing_count + 1

# def test_login(test_app, auth, session):
#     assert test_app.post('/api/v1/login', headers={"Content-Type": "application/json"}, data=json.dumps({})).status_code == 200
#     auth.signup()
#     response = auth.login()
#     assert b'access_token' in response.data
#     assert b'refresh_token' in response.data