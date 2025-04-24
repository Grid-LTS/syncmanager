import os
from pathlib import Path
import shutil
import pytest

# Project files
from syncmanagerclient.main import apply_sync_conf_files, register_local_branch_for_deletion
from syncmanagerclient.clients import ACTION_PULL, ACTION_PUSH

from .utils.testutils import setup_repos, test_dir, var_dir_path, repos_dir, local_repo_path, \
    others_repo_path, local_conf_file_name, others_conf_file_name


@pytest.fixture(scope="module")
def setup_repositories():
    origin_repo, local_repo = setup_repos(local_conf_file_name)
    others_repo = origin_repo.clone(others_repo_path)
    yield origin_repo, local_repo, others_repo
    shutil.rmtree(repos_dir)


def checkout_all_upstream_branches(repo, checkout_these_branches=[]):
    remote_repo = repo.remote('origin')
    for remote_ref in remote_repo.refs:
        name, remote_name = get_branch_name_and_repo_from_remote_path(str(remote_ref))
        if str(remote_ref) in checkout_these_branches and name != 'HEAD':
            print(f'Set up local tracking branch for {str(remote_ref)}')
            create_local_branch_from_remote(repo, name, remote_ref)


def create_local_branch_from_remote(repo, local_branch, remote_branch):
    repo.create_head(local_branch, remote_branch)  # create local branch from remote
    if hasattr(repo.heads, str(local_branch)):
        getattr(repo.heads, str(local_branch)).set_tracking_branch(remote_branch)


def get_branch_name_and_repo_from_remote_path(remote_branch):
    remote_branch = remote_branch.strip()
    parts = remote_branch.split('/')
    return '/'.join(parts[1:]), parts[0]


def test_push_sync(setup_repositories):
    origin_repo, local_repo, others_repo = setup_repositories
    test_file_path = os.path.join(local_repo_path, 'next_file.txt')
    checkout_principal_branch(local_repo)
    Path(test_file_path).touch()
    local_repo.index.add([test_file_path])
    commit_message = "New commit"
    local_repo.index.commit(commit_message)
    # push changes
    apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
    # sync changes to others repo
    apply_sync_conf_files(test_dir, [others_conf_file_name], ACTION_PULL, False, '', ['git'])
    # tests that the HEAD of the other repo points to the synced commit
    last_commit = others_repo.head.commit
    assert last_commit.message == commit_message


def test_delete_branch(setup_repositories):
    origin_repo, local_repo, others_repo = setup_repositories
    # create branch
    test_branch = 'feature/tests'
    local_repo.create_head(test_branch)
    # sync with remote repo
    apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
    apply_sync_conf_files(test_dir, [others_conf_file_name], ACTION_PULL, False, '', ['git'])

    checkout_all_upstream_branches(others_repo, ['origin/' + test_branch])
    # confirm that branch exists in both remote repo and in other repo
    assert hasattr(origin_repo.heads, test_branch)
    assert hasattr(others_repo.heads, test_branch)

    # delete the created branch and sync
    register_local_branch_for_deletion(test_branch, local_repo_path)
    # tests that deleted branch register is present
    assert os.path.exists(os.path.join(var_dir_path, 'git.origin.txt'))
    apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
    # tests that the remote repo is missing the branch
    assert getattr(origin_repo.heads, test_branch, None) is None
    # register should be deleted after sync
    assert not os.path.exists(os.path.join(var_dir_path, 'git.origin.txt'))
    # sync with other repo
    apply_sync_conf_files(test_dir, [others_conf_file_name], ACTION_PULL, False, '', ['git'])
    assert getattr(others_repo.heads, test_branch, None) is None


def test_empty_sync(setup_repositories):
    apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
    apply_sync_conf_files(test_dir, [others_conf_file_name], ACTION_PULL, False, '', ['git'])


def checkout_principal_branch(repo):
    # checkout principal branch
    principal_branch = 'master'
    try:
        getattr(repo.heads, principal_branch)
        repo.heads[principal_branch].checkout()
        return principal_branch
    except:
        pass
    principal_branch = 'main'
    try:
        getattr(repo.heads, principal_branch)
        repo.heads[principal_branch].checkout()
    except AttributeError as e:
        raise e
    return principal_branch
