import os
import os.path as osp
import sys
import urllib
from datetime import datetime, timedelta
from pathlib import Path
import uuid

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
    create_repo_url = "/api/git/repos"
    local_path = "~/code/Python/my_test_ws"
    remote_name = "origin"
    body = {
        'local_path': local_path,
        'remote_name': remote_name,
        'client_env': USER_CLIENT_ENV
    }
    
    response = client.post(create_repo_url, headers=http_headers, json=body)
    assert response.status_code == 200
    server_repo = response.json()
    repo_id = server_repo["id"]
    
    # Create a test file and commit it
    test_file_path = os.path.join(local_repo_path, "test.txt")
    Path(test_file_path).touch()
    repo.index.add(["test.txt"])
    repo.index.commit("Initial commit")
    
    # Set up a remote to the server repository
    remote_url = server_repo["server_path_absolute"]
    if "origin" in [remote.name for remote in repo.remotes]:
        repo.delete_remote("origin")
    repo.create_remote("origin", remote_url)
    
    # Push to the remote repository
    try:
        repo.remote("origin").push("master")
    except GitCommandError:
        # If master branch doesn't exist, try main
        repo.remote("origin").push("main")
    
    # Use the API to update the last_commit_date
    # The PATCH endpoint reads the latest commit and updates last_commit_date
    update_url = f"/api/git/repos/{repo_id}"
    update_response = client.patch(update_url, headers=http_headers)
    assert update_response.status_code == 200
    updated_repo = update_response.json()
    
    # Verify that last_commit_date is now set
    assert updated_repo["last_commit_date"] is not None, "last_commit_date should be set after the update API call"
    
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
    # The filter uses an OR condition that includes repositories that:
    # 1. Have a recent commit (within retention_years) OR
    # 2. Have no last_commit_date OR
    # 3. Haven't been updated recently (older than refresh_rate months)
    #
    # Since our repository has a recent commit (within retention_years),
    # it will be returned REGARDLESS of the refresh_rate value.
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
    
    # The repository WILL be returned because it has a recent commit (within retention_years),
    # which satisfies one of the OR conditions in the filter
    assert len(repos_with_large_refresh_rate) == 1, "Repository should be returned because it has a recent commit"
    
    # Test Case 3: Modify the repository to have old commits and old update date
    # First, we'll create a second repository with old values
    old_repo_path = os.path.join(test_dir, "repos", "old_repo")
    os.makedirs(old_repo_path, exist_ok=True)
    
    # Initialize second git repo
    old_repo = Repo.init(old_repo_path)
    
    # Create second client repository resource
    old_local_path = "~/code/Python/old_repo"
    body = {
        'local_path': old_local_path,
        'remote_name': remote_name,
        'client_env': USER_CLIENT_ENV
    }
    
    old_response = client.post(create_repo_url, headers=http_headers, json=body)
    assert old_response.status_code == 200
    old_server_repo = old_response.json()
    old_repo_id = old_server_repo["id"]
    
    # Create a test file and commit it in the second repo
    old_test_file_path = os.path.join(old_repo_path, "test.txt")
    Path(old_test_file_path).touch()
    old_repo.index.add(["test.txt"])
    old_repo.index.commit("Initial commit")
    
    # Set up a remote to the server repository
    old_remote_url = old_server_repo["server_path_absolute"]
    if "origin" in [remote.name for remote in old_repo.remotes]:
        old_repo.delete_remote("origin")
    old_repo.create_remote("origin", old_remote_url)
    
    # Push to the remote repository
    try:
        old_repo.remote("origin").push("master")
    except GitCommandError:
        # If master branch doesn't exist, try main
        old_repo.remote("origin").push("main")
    
    # Update the last_commit_date
    old_update_url = f"/api/git/repos/{old_repo_id}"
    old_update_response = client.patch(old_update_url, headers=http_headers)
    assert old_update_response.status_code == 200
    
    # Now directly update the database to set old values for last_commit_date and updated
    with app.app.app_context():
        from syncmanagerapi.git.model import GitRepo
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        # Update the repository with old values
        old_repo_entity = GitRepo.query.filter_by(id=old_repo_id).first()
        assert old_repo_entity is not None
        
        # Set last_commit_date to be older than retention_years (3 years + 1 day)
        old_repo_entity.last_commit_date = datetime.now() - relativedelta(years=3, days=1)
        
        # Set updated to be older than refresh_rate (61 months)
        old_repo_entity.updated = datetime.now() - relativedelta(months=61)
        
        db.session.commit()
    
    # Test Case 3: refresh_rate > 0 with old commits and old update date
    # The repository should be returned because it satisfies the third condition of the OR filter
    # (GitRepo.updated <= datetime.now() - relativedelta(months=_refresh_rate))
    query_params = {
        "clientenv": USER_CLIENT_ENV,
        "retention_years": 3,
        "refresh_rate": 60,  # 60 months
        "full_info": True
    }
    refresh_rate_old_url = get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params)
    refresh_rate_old_response = client.get(refresh_rate_old_url, headers=http_headers)
    assert refresh_rate_old_response.status_code == 200
    repos_with_old_values = refresh_rate_old_response.json()
    
    # Both repositories should be returned:
    # - First one because it has a recent commit (within retention_years)
    # - Second one because it has old updates (older than refresh_rate months)
    assert len(repos_with_old_values) == 2, "Both repositories should be returned with refresh_rate=60"
    
    # Verify the second repository is included in the results
    old_repo_found = False
    for repo in repos_with_old_values:
        if repo['git_repo']['id'] == old_repo_id:
            old_repo_found = True
            break
    
    assert old_repo_found, "Repository with old commits and old update date should be returned"
    
    # Test Case 4: Create a scenario where no repositories are returned with non-zero refresh_rate
    # We'll create a temporary test environment and repository with specific conditions
    
    # Create a separate test environment for this scenario
    test_env_name = "REFRESH_RATE_TEST_ENV"
    create_client_env_url = "/api/clientenv"
    client_env_body = {
        "client_env_name": test_env_name
    }
    client_env_response = client.post(create_client_env_url, headers=http_headers, json=client_env_body)
    assert client_env_response.status_code == 204
    
    # Create a repository directly in the database that won't satisfy any of the filter conditions
    with app.app.app_context():
        from syncmanagerapi.git.model import GitRepo, UserGitReposAssoc
        from syncmanagerapi.model import ClientEnv, User
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        # Get the current user
        user = User.user_by_username(sync_api_user['username'])
        
        # Get the test client environment
        test_client_env = ClientEnv.get_client_env(_user_id=user.id, _env_name=test_env_name)
        assert test_client_env is not None
        
        # Create a new repository
        test_repo_id = str(uuid.uuid4())
        test_server_path_rel = "test_repo_filtered_out.git"
        
        # Create the git repo entity with specific conditions
        test_repo = GitRepo(server_path_rel=test_server_path_rel, user_id=user.id)
        test_repo.id = test_repo_id
        
        # Set conditions to NOT satisfy any of the filter criteria:
        # 1. Set last_commit_date to be older than retention_years (3 years + 1 day)
        test_repo.last_commit_date = datetime.now() - relativedelta(years=3, days=1)
        
        # 2. Set updated to be recent (less than refresh_rate months)
        test_repo.updated = datetime.now() - relativedelta(months=30)  # Only 30 months old
        
        db.session.add(test_repo)
        db.session.commit()
        
        # Create the user-repo association
        test_local_path = "~/code/Python/test_repo_filtered_out"
        test_remote_name = "origin"
        
        test_user_repo_assoc = UserGitReposAssoc.create_user_gitrepo_assoc(
            _user_id=user.id,
            _repo_id=test_repo_id,
            _local_path_rel=test_local_path,
            _remote_name=test_remote_name,
            _client_envs=[test_client_env]
        )
        db.session.add(test_user_repo_assoc)
        db.session.commit()
    
    # Test the filter with non-zero refresh_rate
    # The repository should NOT be returned because:
    # 1. It has commits older than retention_years (fails first condition)
    # 2. It has a last_commit_date set (fails second condition)
    # 3. It has been updated recently (fails third condition)
    query_params = {
        "clientenv": test_env_name,
        "retention_years": 3,
        "refresh_rate": 60,  # 60 months
        "full_info": True
    }
    no_results_url = get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params)
    no_results_response = client.get(no_results_url, headers=http_headers)
    assert no_results_response.status_code == 200
    repos_with_no_results = no_results_response.json()
    
    # Verify that no repositories are returned
    assert len(repos_with_no_results) == 0, "No repositories should be returned for this specific configuration"
    
    # Clean up all test resources
    with app.app.app_context():
        from syncmanagerapi.git.model import GitRepo, UserGitReposAssoc
        from syncmanagerapi.model import ClientEnv, User
        
        # Get the current user
        user = User.user_by_username(sync_api_user['username'])
        
        # Clean up the test repository
        UserGitReposAssoc.query.filter_by(repo_id=test_repo_id).delete()
        GitRepo.query.filter_by(id=test_repo_id).delete()
        
        # Clean up the original repositories
        UserGitReposAssoc.query.filter_by(repo_id=repo_id).delete()
        GitRepo.query.filter_by(id=repo_id).delete()
        
        UserGitReposAssoc.query.filter_by(repo_id=old_repo_id).delete()
        GitRepo.query.filter_by(id=old_repo_id).delete()
        
        # Clean up the test environment
        test_client_env = ClientEnv.get_client_env(_user_id=user.id, _env_name=test_env_name)
        if test_client_env:
            db.session.delete(test_client_env)
        
        db.session.commit()
