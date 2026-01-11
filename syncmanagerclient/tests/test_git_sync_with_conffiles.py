import os
from pathlib import Path

import pytest

# Project files
from syncmanagerclient.main import apply_sync_conf_files, register_local_branch_for_deletion
from syncmanagerclient.clients import ACTION_PULL, ACTION_PUSH

from .utils.testutils import test_dir, var_dir_path, \
    get_other_repo_path, local_conf_file_name, others_conf_file_name, checkout_principal_branch, \
    teardown_repos_directory, checkout_all_upstream_branches
from .utils.conffileutils import setup_legacy_sync_repos


@pytest.fixture(scope="module")
def setup_repositories(request):
    origin_repo, local_repo = setup_legacy_sync_repos(local_conf_file_name, request.module.__name__.split(".")[-1])
    others_repo = origin_repo.clone(get_other_repo_path(os.path.dirname(local_repo.working_dir)))
    yield origin_repo, local_repo, others_repo
    teardown_repos_directory([origin_repo, local_repo, others_repo])



def test_push_sync_with_conffiles(setup_repositories):
    origin_repo, local_repo, others_repo = setup_repositories
    test_file_path = os.path.join(local_repo.working_dir, 'next_file.txt')
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
    register_local_branch_for_deletion(test_branch, local_repo.working_dir)
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


def test_empty_sync_with_conf_files(setup_repositories):
    apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
    apply_sync_conf_files(test_dir, [others_conf_file_name], ACTION_PULL, False, '', ['git'])
