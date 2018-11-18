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

    @classmethod
    def setUpClass(cls):
        TEMPLATE_ENVIRONMENT = Environment(
            autoescape=False,
            loader=FileSystemLoader(os.path.join(__class__.test_dir, 'templates')),
            trim_blocks=False)
        origin_repo_path = os.path.join(__class__.repos_dir, 'origin_repo.git')
        local_repo_path = os.path.join(__class__.repos_dir, 'workspace')
        context = {
            'local_path': local_repo_path,
            'origin_path': origin_repo_path
        }
        conf_file = TEMPLATE_ENVIRONMENT.get_template('test.conf.j2').render(context)
        conf_file_name = 'test.conf'
        f = open(os.path.join(__class__.test_dir, conf_file_name), 'w')
        f.write(conf_file)
        f.close()
        if not os.path.exists(__class__.repos_dir):
            os.mkdir(__class__.repos_dir)
        # setup repo
        __class__.origin_repo = Repo.init(origin_repo_path, bare=True)
        __class__.local_repo = Repo.init(local_repo_path)
        __class__.local_repo.create_remote('origin', url=os.path.abspath(__class__.origin_repo.working_dir))
        # add origin_repo as remote
        # create file and commit
        Path(local_repo_path + '/file.txt').touch()
        __class__.local_repo.index.add([local_repo_path + '/file.txt'])
        __class__.local_repo.index.commit("Initial commit on master branch")
        sync_conf_files = [conf_file_name]
        apply_sync_conf_files(__class__.test_dir, sync_conf_files, ACTION_PUSH, False, '', ['git'])

    def test_push_sync(self):
        self.assertTrue('true')

    @classmethod
    def tearDownClass(cls):
        # clean up
        shutil.rmtree(__class__.repos_dir)
