import os.path as osp

from flask import current_app, g
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

import MySQLdb
import sqlite3

from .settings import properties_dir

conf = current_app.config

if current_app.env == 'development' and conf.get('DB_SQLITE_NAME', None):
    path_to_db = osp.join(osp.join(properties_dir, conf.get('INSTALL_DIR')), conf.get('DB_SQLITE_NAME'))
    current_app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{path_to_db}"
else:
    current_app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://{db_user}:{db_password}@{db_host}/{db_schema}".format(
        db_user=conf['DB_USER'], db_password=conf['DB_PASSWORD'], db_host=conf['DB_HOST'],
        db_schema=conf['DB_SCHEMA_NAME'])
db = SQLAlchemy(current_app)
# Initialize Marshmallow
ma = Marshmallow(current_app)


def init_schema():
    # import all the models
    from .git import model
    db.create_all()


def get_database_connection():
    if current_app.env == 'development' and conf.get('DB_SQLITE_NAME', None):
        path_to_db = osp.join(osp.join(properties_dir, conf.get('INSTALL_DIR')), conf.get('DB_SQLITE_NAME'))
        db = sqlite3.connect(path_to_db)
        db_type = "sqlite"
    else:
        db = MySQLdb.connect(host=current_app.config['DB_HOST'], user=current_app.config['DB_USER'],
                             passwd=current_app.config['DB_PASSWORD'], db=current_app.config['DB_SCHEMA_NAME'])
        db_type = "mysql"
    return db, db_type


"""
@current_app.teardown_appcontext
def close_connection(exception):
    if db is not None:
        db.close()
"""
