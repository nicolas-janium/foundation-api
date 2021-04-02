import os

from sqlalchemy import engine

SQLALCHEMY_DATABASE_URI = engine.url.URL(
    drivername='mysql+pymysql',
    username= os.getenv('DB_USER'),
    password= os.getenv('DB_PASSWORD'),
    database= os.getenv('DB_DATABASE'),
    host= os.getenv('DB_HOST'),
    port= os.getenv('DB_PORT') if os.getenv('DB_PORT') else 3306
)
print(SQLALCHEMY_DATABASE_URI)