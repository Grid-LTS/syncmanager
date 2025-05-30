import os
import os.path as osp
from pathlib import Path, PurePosixPath
from git import Repo
from git.exc import GitCommandError

test_dir = os.path.dirname(os.path.abspath(__file__))

home_dir = test_dir

def local_path_rel(local_path):
    system_home_dir=PurePosixPath(Path(home_dir))
    local_path_posix = PurePosixPath(local_path)
    if osp.commonprefix([local_path_posix, system_home_dir]) == system_home_dir.as_posix():
        return '~/' + str(local_path_posix.relative_to(system_home_dir).as_posix())
    else:
        return str(local_path)


def setup_test_repo(client, http_headers, local_repo_path, remote_name, client_env):
    """Helper method to set up a test repository."""

    repo = Repo.init(local_repo_path)
    create_repo_url = "/api/git/repos"
    body = {
        'local_path': local_path_rel(local_repo_path),
        'remote_name': remote_name,
        'client_env': client_env
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
        repo.remote("origin").push("main")
    # Use the API to update the last_commit_date
    update_url = f"/api/git/repos/{repo_id}"
    update_response = client.patch(update_url, headers=http_headers)
    assert update_response.status_code == 200
    updated_repo = update_response.json()
    assert updated_repo["last_commit_date"] is not None, "last_commit_date should be set after the update API call"
    return repo, repo_id



def cleanup_test_resources(client, http_headers, repo_ids):
    """Helper method to clean up all test resources."""
    for repo_id in repo_ids:
        delete_repo_url = f"/api/git/repos/{repo_id}"
        response = client.delete(delete_repo_url, headers=http_headers)
        assert response.status_code == 204