from foundation_api.V1.sa_db.model import User
from uuid import uuid4

# def test_user_model(session):
#     existing_count = session.query(User).count()
#     user = User(str(uuid4()), 'Test', 'User', 'Test', 'Test', 'Test', 'test@test.com', None, '5555555555', 'test', 'test')
#     session.add(user)
#     session.commit()

#     assert session.query(User).count() == existing_count + 1