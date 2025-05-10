import os
import os.path as osp
import sys
import urllib
from datetime import datetime, timedelta
import time
from pathlib import Path

import pytest
from conftest import git_base_dir_path
from git import Repo
from git.exc import GitCommandError

from syncmanagerapi import create_app
from syncmanagerapi.git.model import GitRepo
from syncmanagerapi.settings import get_properties_path

test_dir = os.path.dirname(os.path.abspath(__file__))
syncmanager_api_dir = os.path.dirname(test_dir)
project_dir = os.path.dirname(syncmanager_api_dir)
sys.path.insert(0, project_dir)

from testlib.testsetup import USER_CLIENT_ENV, setup_users_and_env, get_user_basic_authorization
from testlib.api_utility import fetch_client_repo_from_api, get_clientenv_repos_url, headers


@pytest.mark.dependency()
def test_setup(initialized_app, client, sync_api_user):
    setup_users_and_env(client, sync_api_user)


@pytest.mark.dependency(depends=["test_setup"])
def test_create_repo(client, sync_api_user):
    client_env = USER_CLIENT_ENV
    http_headers = headers(sync_api_user)
    response = client.get(get_clientenv_repos_url + f"?clientenv={client_env}", headers=http_headers)
    assert response.status_code == 200
    assert response.json() == []
    # create repo unauthorized
    create_repo_url = "/api/git/repos"
    local_path = "~/code/Python/my_python"
    remote_name = "origin"
    body = {
        'local_path': local_path,
        'remote_name': remote_name,
        'client_env': USER_CLIENT_ENV
    }
    response = client.post(create_repo_url, json=body)
    assert response.status_code == 401
    response = client.post(create_repo_url, headers=http_headers, json=body)
    assert response.status_code == 200
    response_dict = response.json()
    assert response_dict["is_new_reference"]
    assert response_dict["last_commit_date"] is None
    repo_server_path = osp.join(git_base_dir_path, response_dict["server_path_rel"])
    assert response_dict["server_path_absolute"] == repo_server_path
    assert response_dict["remote_name"] == "origin"
    repo_id = response_dict["id"]
    assert len(response_dict["userinfo"]) == 1
    user_git_repo_id = response_dict["userinfo"][0]['id']
    assert bool(repo_id)
    response = client.patch(f"/api/git/repos/{repo_id}", headers=http_headers)
    assert response.status_code == 400

    # test that repo is returned even with applied retention_years filter
    query_params = {
        "clientenv" : USER_CLIENT_ENV,
        "retention_years" : 3
    }
    # fetch all repos
    repo_list_resp = client.get(get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params), headers=http_headers)
    assert repo_list_resp.status_code == 200
    repo_list = repo_list_resp.json()
    assert len(repo_list) == 1
    fetched_created_repo = repo_list[0]
    assert fetched_created_repo['git_repo'] == repo_id
    assert fetched_created_repo['id'] == user_git_repo_id
    assert osp.exists(repo_server_path)


@pytest.mark.dependency(depends=["test_create_repo"])
def test_client_repo_config(client, sync_api_user):
    http_headers = headers(sync_api_user)
    username = "Joe Doe"
    email = "doe@bestcompanyever.com"
    client_env = USER_CLIENT_ENV
    client_repo_to_update = fetch_client_repo_from_api(client, client_env, sync_api_user)
    assert client_repo_to_update["user_name_config"] is None
    assert client_repo_to_update["user_email_config"] is None
    client_repo_to_update["user_name_config"] = username
    client_repo_to_update["user_email_config"] = email
    resp = client.put(f"/api/git/clientrepos/{client_repo_to_update["id"]}", json=client_repo_to_update, headers=http_headers)
    assert resp.status_code == 200
    resp_body = resp.json()
    assert resp_body["user_name_config"] == username
    assert resp_body["user_email_config"] == email

@pytest.mark.dependency(depends=["test_client_repo_config"])
def test_delete_repo(client, sync_api_user):
    http_headers = headers(sync_api_user)
    client_env = USER_CLIENT_ENV
    fetched_repo = fetch_client_repo_from_api(client, client_env, sync_api_user)
    server_repo = fetched_repo['git_repo']
    repo_id = server_repo["id"]
    repo_server_path = osp.join(git_base_dir_path, server_repo["server_path_rel"])

    # delete repo
    delete_repo_url = f"/api/git/repos/{repo_id}"
    response = client.delete(delete_repo_url, headers=http_headers)
    assert response.status_code == 204
    repo_list_resp2 = client.get(get_clientenv_repos_url + f"?clientenv={client_env}", headers=http_headers)
    repo_list2 = repo_list_resp2.json()
    assert len(repo_list2) == 0
    assert not osp.exists(repo_server_path)


@pytest.mark.dependency(depends=["test_create_repo"])
def test_create_repo_for_different_environment(client):
    pass

@pytest.mark.dependency(depends=["test_setup"])
def test_get_repos_refresh_rate(client, app, db, sync_api_user):
    """Test GET /git/repos with refresh_rate parameter"""
    http_headers = headers(sync_api_user)
    client_env = USER_CLIENT_ENV

    # Create local repo directory
    local_repo_path = os.path.join(test_dir, "repos", "my_test_ws")
    os.makedirs(local_repo_path, exist_ok=True)

    # Initialize git repo
    repo = Repo.init(local_repo_path)

    # Create client repository resource
    create_client_repo_url = "/api/git/repos"
    client_repo_body = {
        'local_path': local_repo_path,
        'remote_name': 'origin',
        'client_env': client_env,
        'server_parent_dir_relative': 'Python_repo/test_repo.git'
    }
    client_repo_response = client.post(create_client_repo_url, headers=http_headers, json=client_repo_body)
    assert client_repo_response.status_code == 200

    # Set the remote URL from the server repository
    server_repo = client_repo_response.json()
    
    # Remove existing remote if it exists
    try:
        repo.delete_remote('origin')
    except ValueError:
        pass  # Remote doesn't exist, which is fine
    
    # Create new remote
    repo.create_remote('origin', server_repo['server_path_absolute'])

    # create a commit 
    test_file_path = os.path.join(local_repo_path, "test.txt")
    Path(test_file_path).touch()
    repo.index.add(["test.txt"])
    repo.index.commit("Update test file")
    
    # Push to remote
    origin = repo.remote(name='origin')
    origin.push('master')

    # Fetch client repository and verify
    fetch_url = f"/api/git/repos?clientenv={client_env}&full_info=True"
    fetch_response = client.get(fetch_url, headers=http_headers)
    assert fetch_response.status_code == 200
    client_repos = fetch_response.json()
    assert len(client_repos) == 1
    
    # Verify remote URL matches server_path_absolute
    client_repo = client_repos[0]
    remote_url = repo.remote('origin').url
    assert Path(remote_url).resolve() == Path(client_repo['git_repo']['server_path_absolute']).resolve()
