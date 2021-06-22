from foundation_api.V1.sa_db.model import User, Credentials
from uuid import uuid4

# def test_user_model(session):
#     existing_count = session.query(User).count()
#     user = User(str(uuid4()), Credentials.unassigned_credentials_id, 'Test', 'Test', 'Test', 'Test', 'Test', 'test@test.com', None, '123')
#     session.add(user)
#     session.commit()

#     assert session.query(User).count() == existing_count + 1