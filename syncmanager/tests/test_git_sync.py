import unittest
import os
from git import Repo
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import shutil

# Project files
from syncmanager.main import apply_sync_conf_files
from syncmanager.clients import ACTION_PULL, ACTION_PUSH


class GitClientSyncTest(unittest.TestCase):
    test_dir = os.path.dirname(os.path.abspath(__file__))
    repos_dir = test_dir + '/repos'
    # workspace and others_ws are different downstream clones of the same repo
    # these are called stations here, in reality they are on different computers
    origin_repo_path = os.path.join(repos_dir, 'origin_repo.git')
    local_repo_path = os.path.join(repos_dir, 'workspace')
    others_repo_path = os.path.join(repos_dir, 'others_ws')
    origin_repo = None
    local_repo = None
    others_repo = None
    local_conf_file_name = 'local.conf'
    others_conf_file_name = 'others.conf'

    @classmethod
    def setUpClass(cls):
        TEMPLATE_ENVIRONMENT = Environment(
            autoescape=False,
            loader=FileSystemLoader(os.path.join(__class__.test_dir, 'templates')),
            trim_blocks=False)
        context = {
            'local_path': __class__.local_repo_path,
            'others_path': __class__.others_repo_path,
            'origin_path': __class__.origin_repo_path
        }
        for sync_env in ['local', 'others']:
            conf_file = TEMPLATE_ENVIRONMENT.get_template('{}.conf.j2'.format(sync_env)).render(context)
            conf_file_name = '{}.conf'.format(sync_env)
            f = open(os.path.join(__class__.test_dir, conf_file_name), 'w')
            f.write(conf_file)
            f.close()
        
        if not os.path.exists(__class__.repos_dir):
            os.mkdir(__class__.repos_dir)
        # setup repos
        __class__.origin_repo = Repo.init(__class__.origin_repo_path, bare=True)
        __class__.local_repo = Repo.init(__class__.local_repo_path)
        __class__.local_repo.create_remote('origin', url=os.path.abspath(__class__.origin_repo.working_dir))
        # add origin_repo as remote
        # create file and commit
        test_file_path = os.path.join(__class__.local_repo_path, 'file.txt')
        Path(test_file_path).touch()
        __class__.local_repo.index.add([test_file_path])
        __class__.local_repo.index.commit("Initial commit on master branch")
        apply_sync_conf_files(__class__.test_dir, [__class__.local_conf_file_name], ACTION_PUSH, False, '', ['git'])
        __class__.others_repo = __class__.origin_repo.clone(__class__.others_repo_path)

    def test_push_sync(self):
        """tests when a commit is issued at the one station, it is present at the other station after pulling
        """
        test_file_path = os.path.join(__class__.local_repo_path, 'next_file.txt')
        Path(test_file_path).touch()
        __class__.local_repo.index.add([test_file_path])
        commit_message = "New commit"
        __class__.local_repo.index.commit(commit_message)
        # push changes
        apply_sync_conf_files(__class__.test_dir, [__class__.local_conf_file_name], ACTION_PUSH, False, '', ['git'])
        # sync changes to others repo
        apply_sync_conf_files(__class__.test_dir, [__class__.others_conf_file_name], ACTION_PULL, False, '', ['git'])
        # test that the HEAD of the other repo points to the synced commit
        last_commit = __class__.others_repo.head.commit
        self.assertEqual(last_commit.message,commit_message)

    @classmethod
    def tearDownClass(cls):
        # clean up
        shutil.rmtree(__class__.repos_dir)
