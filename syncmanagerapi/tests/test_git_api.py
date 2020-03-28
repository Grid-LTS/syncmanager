import os.path as osp

import pytest
from setup import USER, USER_PASSWORD, USER_CLIENT_ENV, setup_users_and_env, get_user_basic_authorization
from conftest import sync_manager_server_conf


@pytest.mark.dependency()
def test_setup(client, runner):
    setup_users_and_env(client, runner)


@pytest.mark.dependency(depends=["test_setup"])
def test_create_repo(client):
    client_env = USER_CLIENT_ENV
    get_clientenv_repos_url = f"/api/git/repos/{client_env}"
    headers = {"Authorization": get_user_basic_authorization()}
    response = client.get(get_clientenv_repos_url, headers=headers)
    assert response.status_code == 200
    assert response.json == []
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
    response = client.post(create_repo_url, headers=headers, json=body)
    response_dict = response.json
    assert response_dict["is_new_reference"]
    git_base_dir = osp.join(osp.join(osp.join(sync_manager_server_conf, "local"), "var"), "git")
    assert response_dict["server_path_absolute"] == osp.join(git_base_dir, response_dict["server_path_rel"])
    assert response_dict["remote_name"] == "origin"
    repo_id = response_dict["id"]
    assert len(response_dict["userinfo"]) == 1
    user_git_repo_id = response_dict["userinfo"][0]['id']
    assert bool(repo_id)
    # fetch all repos
    repo_list_resp = client.get(get_clientenv_repos_url, headers=headers)
    repo_list = repo_list_resp.json
    assert len(repo_list) == 1
    fetched_created_repo = repo_list[0]
    assert fetched_created_repo['git_repo'] == repo_id
    assert fetched_created_repo['id'] == user_git_repo_id
    
    
@pytest.mark.dependency(depends=["test_create_repo"])
def test_create_repo_for_different_environment(client):
    pass
    