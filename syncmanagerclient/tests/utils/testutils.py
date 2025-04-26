import os

import shutil
import stat
import time

from syncmanagerclient.util.system import change_dir

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

def teardown_repos_directory(repos=[]):
    try:
        for repo in repos:
            repo.close()
        change_dir(os.path.dirname(repos_dir))
        time.sleep(1)
        shutil.rmtree(repos_dir,onerror=lambda func, path, _: (os.chmod(path, stat.S_IWRITE), func(path)))
    except PermissionError as err:
        print(f"Cannot delete {repos_dir}")
        raise err
