import os
from datetime import timedelta

from sqlalchemy import engine
from dotenv import load_dotenv

load_dotenv()

FLASK_HOST = os.getenv('FLASK_HOST')

SQLALCHEMY_DATABASE_URI = engine.url.URL(
    drivername='mysql+pymysql',
    username= os.getenv('DB_USER'),
    password= os.getenv('DB_PASSWORD'),
    database= os.getenv('DB_NAME'),
    host= os.getenv('DB_HOST'),
    port= os.getenv('DB_PORT', 3306)
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

SECRET_KEY = 'super_secret_key'

JWT_SECRET_KEY = 'super_secret_jwt_key'
# JWT_COOKIE_SECURE = True
# JWT_TOKEN_LOCATION = ["cookies"]
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_DEFAULT_FROM = 'nic@janium.io'