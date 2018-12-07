import unittest
import os
from git import Repo
from pathlib import Path
import shutil

from .utils.testutils import setup_repos, repos_dir, local_conf_file_name


class GitClientSyncTest(unittest.TestCase):
    origin_repo = None
    local_repo = None

    @classmethod
    def setUpClass(cls):
        __class__.origin_repo, __class__.local_repo = setup_repos(local_conf_file_name)

    @classmethod
    def tearDownClass(cls):
        # clean up
        shutil.rmtree(repos_dir)