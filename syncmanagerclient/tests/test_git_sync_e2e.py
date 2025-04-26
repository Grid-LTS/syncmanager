import os
import sys
import tempfile
from threading import Thread

import pytest

from .utils.testutils import local_repo_path

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, project_dir)

from testlib.testsetup import USER_CLIENT_ENV, setup_users_and_env, get_user_basic_authorization
from testlib.fixtures import client, runner


@pytest.fixture(scope="module")
def app():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(test_dir))
    syncmanagerapi_dir = os.path.join(project_dir, "syncmanagerapi")
    sys.path.insert(0, syncmanagerapi_dir)
    db_file_descriptor, db_path = tempfile.mkstemp()
    from syncmanagerapi import create_app
    app = create_app({
        'ENV': 'e2e',
        'DB_SQLITE_PATH': db_path,
        'SYNCMANAGER_SERVER_CONF': syncmanagerapi_dir,
        'DB_RESET': True,
        'SERVER_PORT' : 5100
    })
    thread = Thread(target=app.run, daemon=True, kwargs=dict(host='localhost', port=5100))
    thread.start()
    yield app

@pytest.mark.dependency()
def test_setup(client, runner):
    setup_users_and_env(client, runner)

@pytest.mark.dependency(depends=["test_setup"])
def test_push_sync(app):
    test_file_path = os.path.join(local_repo_path, 'next_file.txt')
