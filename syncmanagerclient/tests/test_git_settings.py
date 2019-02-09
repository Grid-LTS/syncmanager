import unittest
import shutil
import os

from .utils.testutils import setup_repos, repos_dir, local_conf_file_name, test_dir, local_repo_path, origin_repo_path, detemplate_conf
from ..syncmanagerclient.main import apply_sync_conf_files
from ..syncmanagerclient.clients import ACTION_SET_CONF

class GitClientSettingsTest(unittest.TestCase):
    origin_repo = None
    local_repo = None

    @classmethod
    def setUpClass(cls):
        __class__.origin_repo, __class__.local_repo = setup_repos(local_conf_file_name)


    def test_set_config(self):
        mod_user_name = 'Mod User'
        mod_user_email = 'foobaz@test.com'
        mod_origin_path = os.path.join(os.path.dirname(origin_repo_path), 'dummy_repo')
        context = {
            'local_path': local_repo_path,
            'origin_path': mod_origin_path  ,
            'mod_user_name': mod_user_name,
            'mod_user_email': mod_user_email
        }
        mod_env = 'localmod'
        detemplate_conf(mod_env, context)
        apply_sync_conf_files(test_dir, [mod_env + '.conf'], ACTION_SET_CONF, False, '', ['git'])
        conf_reader = __class__.local_repo.config_reader()
        self.assertEqual(conf_reader.get_value('user', 'name'), mod_user_name)
        # check that remote repo url was modified as well
        remote_repo = __class__.local_repo.remote('origin')
        conf_reader_remote = remote_repo.config_reader
        self.assertEqual(conf_reader_remote.get_value("url")[7:], mod_origin_path)

    @classmethod
    def tearDownClass(cls):
        # clean up
        shutil.rmtree(repos_dir)