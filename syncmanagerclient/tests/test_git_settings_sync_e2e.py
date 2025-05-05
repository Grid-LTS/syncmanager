import os
import sys

import urllib
import datetime as dt
from pathlib import Path


import pytest

from syncmanagerclient.main import execute_command
from syncmanagerclient.clients.git_settings import GitClientSettings
from .utils.testutils import load_global_properties, ArgumentsTest

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, project_dir)

from testlib.testsetup import USER_CLIENT_ENV, get_user_basic_authorization
from testlib.api_utility import fetch_client_repo_from_api, get_clientenv_repos_url

import syncmanagerclient.util.globalproperties as globalproperties
from syncmanagerclient.util.syncconfig import SyncConfig

# from .conftest import local_repo, client # DO NOT IMPORT, rely on pytest discovery mechanism via conftest.py

system_tz = dt.datetime.now().astimezone().tzinfo

USER_NAME = __name__.split(".")[-1]
USER_EMAIL = f"{USER_NAME}@test.com"

@pytest.fixture(scope="module", autouse=True)
def init_test(sync_api_user):
    load_global_properties('e2e')
    globalproperties.allconfig.username = USER_NAME
    globalproperties.allconfig.email = USER_EMAIL


def test_set_settings(app_initialized, local_repo, client, sync_api_user):
    client_repo_to_update = fetch_client_repo_from_api(client, USER_CLIENT_ENV, sync_api_user)
    assert client_repo_to_update["user_name_config"] == USER_NAME
    assert client_repo_to_update["user_email_config"] == USER_EMAIL

    assert local_repo.config_reader().get_value("user", "name") == USER_NAME
    assert local_repo.config_reader().get_value("user", "email") == USER_EMAIL
    origin_url = local_repo.remotes["origin"].url

    load_global_properties()
    globalproperties.api_user = sync_api_user["username"]
    globalproperties.api_pw = sync_api_user["password"]

    assert globalproperties.allconfig.username != USER_NAME
    assert globalproperties.allconfig.email != USER_EMAIL

    # artificially overwrite the git config of the repo
    sync_settings = GitClientSettings(SyncConfig.init(local_path_short=local_repo.working_dir, allconfig=globalproperties.allconfig), local_repo)
    sync_settings.set_user_config()

    assert local_repo.config_reader().get_value("user", "name") == globalproperties.allconfig.username
    assert local_repo.config_reader().get_value("user", "email") == globalproperties.allconfig.email

    sync_config = SyncConfig.init(allconfig = globalproperties.allconfig)

    args = ArgumentsTest()
    args.action = "set-config"
    execute_command(args, sync_config, remote_name="origin")
    assert local_repo.config_reader().get_value("user", "name") == USER_NAME
    assert local_repo.config_reader().get_value("user", "email") == USER_EMAIL
    assert Path(local_repo.remotes["origin"].url) == Path(origin_url)

def fetch_server_repo(client, client_env, sync_api_user):
    headers = {"Authorization": get_user_basic_authorization(sync_api_user)}
    query_params = {
        "clientenv": client_env,
        "full_info": True
    }
    get_clientenv_repos_url = f"/api/git/repos"
    response = client.get(get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params), headers=headers)
    local_repo_api = response.json()[0]
    return local_repo_api['git_repo']
