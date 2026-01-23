import os
import sys

from pathlib import Path
import urllib
import datetime as dt
from git import Repo
import shutil

import pytest

from syncmanagerclient.main import execute_command
from syncmanagerclient.util.syncconfig import SyncConfig
from syncmanagerclient.util.globalproperties import Globalproperties, resolve_repo_path
from syncmanagerclient.util.system import change_dir

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, project_dir)

from testlib.testsetup import USER_CLIENT_ENV, USER_CLIENT_ENV_EXTRA, get_user_basic_authorization

from .utils.testutils import checkout_principal_branch, ArgumentsTest, get_other_repo_path, \
    checkout_all_upstream_branches, load_global_properties
from .conftest import e2e_test_workspace_root  # DO NOT IMPORT fixtures, rely on pytest discovery mechanism via

# conftest.py

system_tz = dt.datetime.now().astimezone().tzinfo

"""
Define or import fixtures functions only in conftest.py
"""

other_repo_path = ''

USER_NAME = __name__.split(".")[-1]
USER_EMAIL = f"{USER_NAME}@test.com"


@pytest.fixture(scope="module")
def init_test(sync_api_user):
    repos_root_dir = os.path.join(e2e_test_workspace_root, sync_api_user["username"], "e2e")
    load_global_properties(repos_root_dir=repos_root_dir)


@pytest.mark.dependency()
def test_push_sync(app_initialized, local_repo, client, sync_api_user):
    global other_repo_path
    get_clientenv_repos_url = f"/api/git/repos"
    headers = {"Authorization": get_user_basic_authorization(sync_api_user)}
    query_params = {
        "clientenv": USER_CLIENT_ENV,
        "full_info": True
    }
    response = client.get(get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params), headers=headers)
    assert response.status_code == 200
    local_repo_api = response.json()[0]
    assert local_repo_api['user_name_config']
    assert local_repo_api['user_email_config']

    remote_repo_api = local_repo_api['git_repo']
    response = client.patch(f"/api/git/repos/{remote_repo_api["id"]}", headers=headers)
    assert response.status_code == 400

    # 2. test first sync
    sync_config = SyncConfig.init(allconfig=Globalproperties.allconfig)

    args = ArgumentsTest()
    args.action = "push"
    args.namespace = "e2e_repo"
    sync_config.remote_repo = "origin"
    execute_command(args, sync_config)

    remote_repo_api = fetch_server_repo(client, USER_CLIENT_ENV, sync_api_user)
    # verify that the remote repo has been updated
    assert remote_repo_api["last_commit_date"] is not None

    checkout_principal_branch(local_repo)
    test_file_path = os.path.join(local_repo.working_dir, 'next_file.txt')

    Path(test_file_path).touch()
    local_repo.index.add([test_file_path])
    commit_message = "New commit"
    new_commit = local_repo.index.commit(commit_message)

    args = ArgumentsTest()
    args.action = "push"
    sync_config.remote_repo = "origin"
    execute_command(args, sync_config)
    remote_repo_api = fetch_server_repo(client, USER_CLIENT_ENV, sync_api_user)
    assert dt.datetime.fromisoformat(remote_repo_api["last_commit_date"]).replace(
        tzinfo=system_tz) == new_commit.committed_datetime

    other_repo_path = get_other_repo_path(os.path.join(e2e_test_workspace_root, sync_api_user["username"], 'e2e-extra'))
    local_repo.close()
    local_repo_path = local_repo.working_dir
    shutil.move(str(local_repo_path), str(other_repo_path))

    # 4. test sync to other environment
    args = ArgumentsTest()
    args.action = "pull"
    sync_config.remote_repo = "origin"
    execute_command(args, sync_config)
    assert os.path.exists(local_repo_path)

    # 5. Finally make re-associate the original repo to the server with the new path
    args = ArgumentsTest()
    args.namespace = "e2e_repo"
    args.action = "set-remote"
    args.env = USER_CLIENT_ENV_EXTRA
    change_dir(other_repo_path)
    change_environment('e2e-extra', sync_api_user)
    Globalproperties.init_allconfig(args)
    sync_config_other = SyncConfig.init(allconfig=Globalproperties.allconfig)
    sync_config_other.remote_repo = "origin"
    execute_command(args, sync_config_other)
    query_params = {
        "clientenv": USER_CLIENT_ENV_EXTRA,
        "full_info": True
    }
    other_repo_api_resp = client.get(get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params),
                                     headers=headers)
    assert other_repo_api_resp.status_code == 200
    other_repos = other_repo_api_resp.json()
    assert len(other_repos) == 1
    assert str(resolve_repo_path(other_repos[0]['local_path_rel'])) == other_repo_path


@pytest.mark.dependency(depends=["test_push_sync"])
def test_delete_branch(app_initialized, local_repo, client, sync_api_user):
    global other_repo_path
    local_repo_path = local_repo.working_dir
    # 0. create branch
    test_branch = 'feature/test-for-deletion'
    change_dir(local_repo_path)
    local_repo = Repo(local_repo_path)
    local_repo.create_head(test_branch)

    # 1. sync with server, branch is pushed
    args = ArgumentsTest()
    args.action = "push"
    args.namespace = "e2e_repo"
    args.sync_env = USER_CLIENT_ENV
    change_environment('e2e', sync_api_user, args)

    sync_config = SyncConfig.init(allconfig=Globalproperties.allconfig)
    sync_config.remote_repo = "origin"
    execute_command(args, sync_config)

    # 2. change to extra env and fetch the branch
    args = ArgumentsTest()
    args.action = "pull"
    args.namespace = "e2e_repo"
    args.env = USER_CLIENT_ENV_EXTRA
    change_environment('e2e-extra', sync_api_user, args)

    other_sync_config = SyncConfig.init(allconfig=Globalproperties.allconfig)
    other_sync_config.remote_repo = "origin"
    execute_command(args, other_sync_config)

    # after sync the file system pointer points to the parent dir of the repositories
    assert os.getcwd() == Globalproperties.allconfig.global_config.filesystem_root_dir
    assert os.path.basename(os.path.dirname(other_repo_path)) == "e2e-extra"

    other_repo = Repo(other_repo_path)
    checkout_all_upstream_branches(other_repo, ['origin/' + test_branch])

    syncmanagerapi_dir = app_initialized.app.config.get("SYNCMANAGER_SERVER_CONF")
    server_repo = Repo(os.path.join(syncmanagerapi_dir, "tests", "var", "git", sync_api_user["id"], args.namespace,
                                    f"{os.path.basename(local_repo_path)}.git"))

    # confirm that branch exists in both remote repo and in other repo
    assert hasattr(server_repo.heads, test_branch)
    assert hasattr(local_repo.heads, test_branch)
    assert hasattr(other_repo.heads, test_branch)

    # Step 3: Delete the branch in the initial repo
    change_dir(local_repo_path)
    change_environment('e2e', sync_api_user)
    args = ArgumentsTest()
    args.action = "delete"
    sync_config.remote_repo = "origin"
    execute_command(args, sync_config, path=test_branch)
    # branch is deleted on local workspace only
    assert not hasattr(local_repo.heads, test_branch)
    assert hasattr(server_repo.heads, test_branch)
    assert hasattr(Repo(other_repo_path).heads, test_branch)

    # registry entry exists
    registry_file_path = os.path.join(Globalproperties.var_dir, 'git.origin.txt')
    assert os.path.exists(registry_file_path), f"deletion registry file missing {registry_file_path}"
    with open(registry_file_path) as file:
        lines = [line.rstrip() for line in file]
    assert test_branch in lines[0]

    # step 4: sync to server
    args = ArgumentsTest()
    args.action = "push"
    sync_config.remote_repo = "origin"
    execute_command(args, sync_config, path=test_branch)
    assert not hasattr(server_repo.heads, test_branch)

    # registry file should be removed
    assert not os.path.exists(registry_file_path)

    # Step 5: Sync other environment, verify branch is now deleted there as well
    change_environment('e2e-extra', sync_api_user)
    args = ArgumentsTest()
    args.action = "pull"
    args.sync_env = USER_CLIENT_ENV_EXTRA
    other_sync_config.remote_repo = "origin"
    execute_command(args, other_sync_config)
    assert not hasattr(other_repo.heads, test_branch)


@pytest.mark.dependency(depends=["test_delete_branch"])
def test_delete_remote_repo(app_initialized, local_repo, client, sync_api_user):
    local_repo_path = local_repo.working_dir
    sync_config = SyncConfig.init(allconfig=Globalproperties.allconfig)
    #  delete remote server repo
    change_dir(local_repo_path)
    args = ArgumentsTest()
    args.action = "delete-repo"
    sync_config.remote_repo = "origin"
    execute_command(args, sync_config)
    remote_repo_api = fetch_server_repo(client, USER_CLIENT_ENV, sync_api_user)
    assert remote_repo_api is None


def fetch_server_repo(client, client_env, sync_api_user):
    headers = {"Authorization": get_user_basic_authorization(sync_api_user)}
    query_params = {
        "clientenv": client_env,
        "full_info": True
    }
    get_clientenv_repos_url = f"/api/git/repos"
    response = client.get(get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params), headers=headers)
    if len(response.json()) == 0:
        return None
    local_repo_api = response.json()[0]
    return local_repo_api['git_repo']


def change_environment(clientenv, sync_api_user, args=None):
    """
    # stage is not to be confused with sync env = clientenv. we don't have the possiblity of test with a physically different
    # environment so we introduce another stage that allows us to configure a different environment/machine
    :param clientenv:
    :param sync_api_user:
    :return:
    """
    Globalproperties.loaded = False
    load_global_properties(clientenv, args=args)
    Globalproperties.allconfig.username = USER_NAME
    Globalproperties.allconfig.email = USER_EMAIL
    Globalproperties.username = sync_api_user["username"]
    Globalproperties.api_pw = sync_api_user["password"]
