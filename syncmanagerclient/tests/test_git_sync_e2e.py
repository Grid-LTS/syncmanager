import os
import sys
import tempfile
from threading import Thread
from pathlib import Path
import urllib
import datetime as dt

import pytest

from syncmanagerclient.main import execute_command

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, project_dir)

from testlib.testsetup import USER_CLIENT_ENV, setup_users_and_env, get_user_basic_authorization
from testlib.fixtures import client, runner, empty_directory

from .utils.testutils import local_repo_path, checkout_principal_branch, teardown_repos_directory
from .utils.e2eutils import setup_local_repo

system_tz = dt.datetime.now().astimezone().tzinfo
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


def test_push_sync(app, local_repo, client):
    get_clientenv_repos_url = f"/api/git/repos"
    headers = {"Authorization": get_user_basic_authorization()}
    query_params = {
        "clientenv": USER_CLIENT_ENV,
        "full_info": True
    }
    response = client.get(get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params), headers=headers)
    assert response.status_code == 200
    local_repo_api = response.json()[0]
    remote_repo_api = local_repo_api['git_repo']
    response = client.patch(f"/api/git/repos/{remote_repo_api["id"]}", headers=headers)
    assert response.status_code == 400

    # 2. test first sync
    execute_command('push', "git", USER_CLIENT_ENV, "e2e_repo", "origin")

    remote_repo_api = fetch_server_repo(client, USER_CLIENT_ENV)
    # verify that the remote repo has been updated
    assert remote_repo_api["last_commit_date"] is not None

    checkout_principal_branch(local_repo)
    test_file_path = os.path.join(local_repo_path, 'next_file.txt')

    Path(test_file_path).touch()
    local_repo.index.add([test_file_path])
    commit_message = "New commit"
    new_commit = local_repo.index.commit(commit_message)
    execute_command('push', "git", USER_CLIENT_ENV, "e2e_repo", "origin")
    remote_repo_api = fetch_server_repo(client, USER_CLIENT_ENV)
    assert dt.datetime.fromisoformat(remote_repo_api["last_commit_date"]).replace( tzinfo=system_tz) == new_commit.committed_datetime

def fetch_server_repo(client, client_env):
    headers = {"Authorization": get_user_basic_authorization()}
    query_params = {
        "clientenv": client_env,
        "full_info": True
    }
    get_clientenv_repos_url = f"/api/git/repos"
    response = client.get(get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params), headers=headers)
    local_repo_api = response.json()[0]
    return local_repo_api['git_repo']
