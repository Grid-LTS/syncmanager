import os
import sys

from pathlib import Path
import urllib
import datetime as dt

from syncmanagerclient.main import execute_command

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, project_dir)

from testlib.testsetup import USER_CLIENT_ENV, get_user_basic_authorization
from testlib.api_utility import fetch_client_repo_from_api, get_clientenv_repos_url

import syncmanagerclient.util.globalproperties as globalproperties

from .utils.testutils import get_local_repo_path, checkout_principal_branch
# from .conftest import local_repo # DO NOT IMPORT, rely on pytest discovery mechanism

system_tz = dt.datetime.now().astimezone().tzinfo


def test_set_settings(app_initialized, local_repo, client, sync_api_user):
    client_repo_to_update = fetch_client_repo_from_api(client, USER_CLIENT_ENV, sync_api_user)
    assert client_repo_to_update["user_name_config"] == globalproperties.gitconfig.username
    assert client_repo_to_update["user_email_config"] == globalproperties.gitconfig.email


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
