import os
import sys
import logging

import pytest
import tempfile

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, project_dir)

from testlib.fixtures import sync_api_user, client, runner, empty_directory
from testlib.testsetup import create_admin

sync_manager_server_conf = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
var_dir_path = os.path.join("tests", "var")
sync_base_dir_path = os.path.join(sync_manager_server_conf, var_dir_path)
git_base_dir_path = os.path.join(sync_base_dir_path, "git")


@pytest.fixture(scope="module")
def app():
    logging.getLogger('flask_sqlalchemy').setLevel(logging.WARNING)
    db_file_descriptor, db_path = tempfile.mkstemp()
    from syncmanagerapi import create_app
    app = create_app({
        'TESTING': True,
        'ENV': 'test',
        'DB_SQLITE_PATH': db_path,
        'SYNCMANAGER_SERVER_CONF': sync_manager_server_conf,
        'DB_RESET': True,
        'SQLALCHEMY_ECHO': False 
    })
    yield app
    with app.app.app_context():
        db_instance = app.app.extensions["sqlalchemy"]
        db_instance.session.close()
        db_instance.engine.dispose()
    # tear down code
    try:
        os.close(db_file_descriptor)
        os.unlink(db_path)
    except PermissionError as perm:
        print(f"Database file could not be cleaned up")
        raise perm
    empty_directory(git_base_dir_path)


@pytest.fixture(scope="module")
def initialized_app(app, runner):
    create_admin(runner)

@pytest.fixture(scope="module")
def db(app):
    """Provides access to the SQLAlchemy database instance."""
    return app.app.extensions["sqlalchemy"]

