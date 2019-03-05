from flask import current_app, g
from flask_sqlalchemy import SQLAlchemy

conf = current_app.config
current_app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://{db_user}:{db_password}@{db_host}/{db_schema}".format(
    db_user=conf['DB_USER'], db_password=conf['DB_PASSWORD'], db_host=conf['DB_HOST'],
    db_schema=conf['DB_SCHEMA_NAME'])
db = SQLAlchemy(current_app)


def init_schema():
    db.create_all()
