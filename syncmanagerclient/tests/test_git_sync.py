import unittest
import os
from pathlib import Path
import shutil

# Project files
from syncmanagerclient.main import apply_sync_conf_files, register_local_branch_for_deletion
from syncmanagerclient.clients import ACTION_PULL, ACTION_PUSH

from .utils.testutils import setup_repos, test_dir, var_dir_path, repos_dir, local_repo_path, \
    others_repo_path, local_conf_file_name, others_conf_file_name


class GitClientSyncTest(unittest.TestCase):
    origin_repo = None
    local_repo = None
    others_repo = None

    @classmethod
    def setUpClass(cls):
        __class__.origin_repo, __class__.local_repo = setup_repos(local_conf_file_name)
        __class__.others_repo = __class__.origin_repo.clone(others_repo_path)

    def test_push_sync(self):
        """
        tests when a commit is issued at the one station, it is present at the other station after pulling
        """
        test_file_path = os.path.join(local_repo_path, 'next_file.txt')
        # checkout master branch
        __class__.local_repo.heads['master'].checkout()
        Path(test_file_path).touch()
        __class__.local_repo.index.add([test_file_path])
        commit_message = "New commit"
        __class__.local_repo.index.commit(commit_message)
        # push changes
        apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
        # sync changes to others repo
        apply_sync_conf_files(test_dir, [others_conf_file_name], ACTION_PULL, False, '', ['git'])
        # tests that the HEAD of the other repo points to the synced commit
        last_commit = __class__.others_repo.head.commit
        self.assertEqual(last_commit.message, commit_message)

    def test_delete_branch(self):
        """
        tests when deleting a branch in one local repo and syncing it with the remote repo, the branch will be deleted 
        in other repo on next sync 
        :return: None
        """
        # create branch
        test_branch = 'feature/tests'
        __class__.local_repo.create_head(test_branch)
        # sync with remote repo
        apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
        apply_sync_conf_files(test_dir, [others_conf_file_name], ACTION_PULL, False, '', ['git'])

        self.checkout_all_upstream_branches(__class__.others_repo, ['origin/' + test_branch])
        # confirm that branch exists in both remote repo and in other repo
        self.assertTrue(getattr(__class__.origin_repo.heads, test_branch))
        self.assertTrue(getattr(__class__.others_repo.heads, test_branch))
        
        # delete the created branch and sync
        register_local_branch_for_deletion(test_branch, local_repo_path)
        # tests that deleted branch register is present
        self.assertTrue(os.path.exists(os.path.join(var_dir_path, 'git.origin.txt')))
        apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
        # tests that the remote repo is missing the branch
        self.assertEqual(getattr(__class__.origin_repo.heads, test_branch, None), None)
        # register should be deleted after sync
        self.assertTrue(not os.path.exists(os.path.join(var_dir_path, 'git.origin.txt')))
        # sync with other repo
        apply_sync_conf_files(test_dir, [others_conf_file_name], ACTION_PULL, False, '', ['git'])
        self.assertEqual(getattr(__class__.others_repo.heads, test_branch, None), None)


    def test_empty_sync(self):
        apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
        apply_sync_conf_files(test_dir, [others_conf_file_name], ACTION_PULL, False, '', ['git'])

    @classmethod
    def tearDownClass(cls):
        # clean up
        shutil.rmtree(repos_dir)

    # Helper methods
    def checkout_all_upstream_branches(self, repo, checkout_theses_branches = []):
        remote_repo = repo.remote('origin')
        for remote_ref in remote_repo.refs:
            name, remote_name = self.get_branch_name_and_repo_from_remote_path(str(remote_ref))
            if str(remote_ref) in checkout_theses_branches and not name == 'HEAD':
                print('Set up local tracking branch for {}'.format(str(remote_ref)))
                self.create_local_branch_from_remote(repo, name, remote_ref)
            
    def create_local_branch_from_remote(self, repo, local_branch, remote_branch):
        repo.create_head(local_branch, remote_branch)  # create local branch from remote
        if hasattr(repo.heads, str(local_branch)):
            getattr(repo.heads, str(local_branch)).set_tracking_branch(remote_branch)

    def get_branch_name_and_repo_from_remote_path(self, remote_branch):
        remote_branch = remote_branch.strip()
        parts = remote_branch.split('/')
        return '/'.join(parts[1:]), parts[0]