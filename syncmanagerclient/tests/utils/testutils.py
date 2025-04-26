import os
import shutil
import stat
import time

from pathlib import Path
from syncmanagerclient.util.system import change_dir


from jinja2 import Environment, FileSystemLoader
from git import Repo

# Project files
from syncmanagerclient.main import apply_sync_conf_files, register_local_branch_for_deletion
from syncmanagerclient.clients import ACTION_PULL, ACTION_PUSH
import syncmanagerclient.util.globalproperties as globalproperties

test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
var_dir_path = os.path.join(test_dir, 'var')
# workspace and others_ws are different downstream clones of the same repo
# these are called stations here, in reality they are on different computer
repos_dir = os.path.join(test_dir, 'repos')
origin_repo_path = os.path.join(repos_dir, 'origin_repo.git')
local_repo_path = os.path.join(repos_dir, 'workspace')
others_repo_path = os.path.join(repos_dir, 'others_ws')
local_conf_file_name = 'local.conf'
others_conf_file_name = 'others.conf'

test_user_name = 'Test User'
test_user_email = 'dummy@tests.com'

