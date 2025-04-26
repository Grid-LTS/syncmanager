import os.path as osp

import pytest
from setup import USER_CLIENT_ENV, setup_users_and_env, get_user_basic_authorization
from conftest import git_base_dir_path


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
    response = client.post(create_repo_url, headers=headers, json=body)
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
    response = client.patch(f"/api/git/repos/{repo_id}", headers=headers)
    assert response.status_code == 400
    # fetch all repos
    repo_list_resp = client.get(get_clientenv_repos_url, headers=headers)
    repo_list = repo_list_resp.json()
    assert len(repo_list) == 1
    fetched_created_repo = repo_list[0]
    assert fetched_created_repo['git_repo'] == repo_id
    assert fetched_created_repo['id'] == user_git_repo_id
    # delete repo
    delete_repo_url = f"/api/git/repos/{repo_id}"
    assert osp.exists(repo_server_path)
    response = client.delete(delete_repo_url, headers=headers)
    assert response.status_code == 204
    repo_list_resp2 = client.get(get_clientenv_repos_url, headers=headers)
    repo_list2 = repo_list_resp2.json()
    assert len(repo_list2) == 0
    assert not osp.exists(repo_server_path)


@pytest.mark.dependency(depends=["test_create_repo"])
def test_create_repo_for_different_environment(client):
    pass
