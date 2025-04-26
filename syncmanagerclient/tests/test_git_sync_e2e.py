import os
import sys
import tempfile
from threading import Thread
from pathlib import Path

import pytest

from syncmanagerclient.main import execute_command

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, project_dir)

from testlib.testsetup import USER_CLIENT_ENV, setup_users_and_env, get_user_basic_authorization
from testlib.fixtures import client, runner, empty_directory

from .utils.testutils import local_repo_path, checkout_principal_branch, teardown_repos_directory
from .utils.e2eutils import setup_local_repo


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
        'SERVER_PORT': 8010
    })
    thread = Thread(target=app.run, daemon=True, kwargs=dict(host='localhost', port=8010))
    thread.start()
    yield app
    git_base_dir_path = app.app.config["FS_ROOT"]
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
def local_repo(client, runner):
    setup_users_and_env(client, runner)
    local_repo = setup_local_repo()
    yield local_repo
    teardown_repos_directory([local_repo])


@pytest.mark.dependency(depends=["local_repo"])
def test_push_sync(app, local_repo):
    test_file_path = os.path.join(local_repo_path, 'next_file.txt')
    execute_command('push', "git", USER_CLIENT_ENV, "e2e_repo", "origin")
    checkout_principal_branch(local_repo)
    Path(test_file_path).touch()
    local_repo.index.add([test_file_path])
    commit_message = "New commit"
    local_repo.index.commit(commit_message)
