import os
import os.path as osp
import sys
import urllib
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pytest
from conftest import git_base_dir_path

test_dir = os.path.dirname(os.path.abspath(__file__))
syncmanager_api_dir = os.path.dirname(test_dir)
project_dir = os.path.dirname(syncmanager_api_dir)
sys.path.insert(0, project_dir)

from testlib.testsetup import USER_CLIENT_ENV, get_user_basic_authorization
from testlib.api_utility import fetch_client_repo_from_api, get_clientenv_repos_url, headers
from testsetup import setup_test_repo, cleanup_test_resources



@pytest.mark.dependency()
def test_create_repo(app_with_user, client, sync_api_user):
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


def test_get_repos_refresh_rate(app_with_user, client, sync_api_user):
    """Test GET /git/repos with refresh_rate parameter"""
    http_headers = headers(sync_api_user)
    client_env = USER_CLIENT_ENV

    # Create local repo directory
    local_repo_path = os.path.join(test_dir, "repos", "my_test_ws")
    os.makedirs(local_repo_path, exist_ok=True)

    # Set up the first test repository
    repo, repo_id = setup_test_repo(client, http_headers, local_repo_path, "origin", client_env)

    # Test Case 1: refresh_rate = 0 (all repositories should be returned)
    query_params = {
        "clientenv": USER_CLIENT_ENV,
        "retention_years": 3,
        "refresh_rate": 0,
        "full_info": True
    }
    refresh_rate_0_url = get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params)
    refresh_rate_0_response = client.get(refresh_rate_0_url, headers=http_headers)
    assert refresh_rate_0_response.status_code == 200
    repos_with_refresh_rate_0 = refresh_rate_0_response.json()
    assert len(repos_with_refresh_rate_0) == 1, "With refresh_rate=0, all repositories should be returned"

    # Test Case 2: refresh_rate > 0
    query_params = {
        "clientenv": USER_CLIENT_ENV,
        "retention_years": 3,
        "refresh_rate": 60,  # Large value in months
        "full_info": True
    }
    refresh_rate_large_url = get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params)
    refresh_rate_large_response = client.get(refresh_rate_large_url, headers=http_headers)
    assert refresh_rate_large_response.status_code == 200
    repos_with_large_refresh_rate = refresh_rate_large_response.json()
    assert len(repos_with_large_refresh_rate) == 1, "Repository should be returned because it has a recent commit"

    # Test Case 3: Create a second, "inactive" repository with old date for last commit, > 3 years
    old_repo_path = os.path.join(test_dir, "repos", "old_repo")
    os.makedirs(old_repo_path, exist_ok=True)
    old_repo, old_repo_id = setup_test_repo(client, http_headers, old_repo_path, "origin", client_env)
    """Helper method to set old values for a repository."""
    with app_with_user.app.app_context():
        db = app_with_user.app.extensions["sqlalchemy"]
        from syncmanagerapi.git.model import GitRepo
        repo_entity = GitRepo.query.filter_by(id=repo_id).first()
        assert repo_entity is not None
        repo_entity.last_commit_date = datetime.now() - relativedelta(years=3, days=1)
        repo_entity.updated = datetime.now() - relativedelta(months=61)
        db.session.commit()


    # Test Case 3: Verify both repositories are returned
    query_params = {
        "clientenv": USER_CLIENT_ENV,
        "retention_years": 3,
        "refresh_rate": 60,
        "full_info": True
    }
    refresh_rate_old_url = get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params)
    refresh_rate_old_response = client.get(refresh_rate_old_url, headers=http_headers)
    assert refresh_rate_old_response.status_code == 200
    repos_with_old_values = refresh_rate_old_response.json()
    assert len(repos_with_old_values) == 2, "Both repositories should be returned with refresh_rate=60"
    old_repo_found = False
    for repo in repos_with_old_values:
        if repo['git_repo']['id'] == old_repo_id:
            old_repo_found = True
            break
    assert old_repo_found, "Repository with old commits and old update date should be returned"
    # Clean up all test resources
    cleanup_test_resources(client, http_headers,[repo_id, old_repo_id])

def test_do_not_refresh_repo_with_recent_enough_refresh(app_with_user, client, sync_api_user):
    """
     # Test Case: a inactive repository is filtered out because refreshed recently
    """
    http_headers = headers(sync_api_user)
    client_env = USER_CLIENT_ENV
    repo_is_filtered_out_path = "test_repo_filtered_out"
    repo_is_filtered_out_path = os.path.join(test_dir, "repos", repo_is_filtered_out_path)
    os.makedirs(repo_is_filtered_out_path, exist_ok=True)

    test_env_name, test_repo_id = setup_test_repo(client, http_headers, repo_is_filtered_out_path, "origin", client_env)

    with app_with_user.app.app_context():
        db = app_with_user.app.extensions["sqlalchemy"]
        from syncmanagerapi.git.model import GitRepo
        test_repo =  repo_entity = GitRepo.query.filter_by(id=test_repo_id).first()
        assert repo_entity is not None
        test_repo.id = test_repo_id
        test_repo.last_commit_date = datetime.now() - relativedelta(years=3, days=1)
        test_repo.updated = datetime.now() - relativedelta(months=30)
        db.session.add(test_repo)
        db.session.commit()


    # Test that no repositories are returned for this configuration
    query_params = {
        "clientenv": USER_CLIENT_ENV,
        "retention_years": 3,
        "refresh_rate": 60,
        "full_info": True
    }
    no_results_url = get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params)
    no_results_response = client.get(no_results_url, headers=http_headers)
    assert no_results_response.status_code == 200
    repos_with_no_results = no_results_response.json()
    assert len(repos_with_no_results) == 0, "No repositories should be returned for this specific configuration"
    cleanup_test_resources(client, http_headers, [test_repo_id])
