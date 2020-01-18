import os.path as osp

from flask import current_app, g
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

from .settings import properties_dir


def init_schema():
    # import all the models
    from .git import model
    db.create_all()


def get_sqlite_path(conf):
    if not conf.get('DB_SQLITE_NAME', None):
        exit(1)
    if conf.get("DB_SQLITE_PATH", None):
        return conf["DB_SQLITE_PATH"]
    return osp.join(osp.join(properties_dir, conf.get('INSTALL_DIR')), conf.get('DB_SQLITE_NAME'))


def get_database_url(app):
    conf = app.config
    if app.env == 'development' or app.env == 'test':
        path_to_db = get_sqlite_path(conf)
        return f"sqlite:///{path_to_db}"
    else:
        return "mysql://{db_user}:{db_password}@{db_host}/{db_schema}".format(
            db_user=conf['DB_USER'], db_password=conf['DB_PASSWORD'], db_host=conf['DB_HOST'],
            db_schema=conf['DB_SCHEMA_NAME'])


def get_database_connection(app):
    conf = app.config
    if app.env == 'development' or app.env == 'test':
        import sqlite3
        path_to_db = get_sqlite_path(conf)
        db = sqlite3.connect(path_to_db)
        db_type = "sqlite"
    else:
        import MySQLdb
        db = MySQLdb.connect(host=conf['DB_HOST'], user=conf['DB_USER'],
                             passwd=conf['DB_PASSWORD'], db=conf['DB_SCHEMA_NAME'])
        db_type = "mysql"
    return db, db_type


current_app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url(current_app)
db = SQLAlchemy(current_app)
# Initialize Marshmallow
ma = Marshmallow(current_app)


def reset_db_connection():
    global current_app
    global db
    global ma
    current_app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url(current_app)
    db.init_app(current_app)
    # Initialize Marshmallow
    ma = Marshmallow(current_app)


"""
@current_app.teardown_appcontext
def close_connection(exception):
    if db is not None:
        db.close()
"""
