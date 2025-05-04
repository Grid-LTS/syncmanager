import os

import shutil
import stat
import time

from syncmanagerclient.util.system import change_dir
import syncmanagerclient.util.globalproperties as globalproperties
from syncmanagerclient.main import init_global_properties

from testlib.testsetup import USER_CLIENT_ENV

test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
var_dir_path = os.path.join(test_dir, 'var')
# workspace and others_ws are different downstream clones of the same repo
# these are called stations here, in reality they are on different computer
get_origin_repo_path = lambda repos_dir:  build_local_repo_path(repos_dir, 'origin_repo.git')
get_local_repo_path = lambda repos_dir: build_local_repo_path(repos_dir, 'workspace')
get_others_repo_path = lambda repos_dir: build_local_repo_path(repos_dir, 'others_ws')
local_conf_file_name = 'local.conf'
others_conf_file_name = 'others.conf'

test_user_name = 'Test User'
test_user_email = 'dummy@tests.com'

class ArgumentsTest:

    def __init__(self):
        self.action = None
        self.namespace = "e2e_repo"
        self.force = False
        self.client = 'git'
        self.sync_env = USER_CLIENT_ENV


def load_global_properties():
    init_global_properties("e2e")
    globalproperties.set_prefix(os.path.dirname(test_dir))
    globalproperties.test_mode = True

def build_local_repo_path(parent_dir, base):
    if not parent_dir:
        raise ValueError(f"Base dir for repos must not be empty")
    return os.path.join(parent_dir, base)

def teardown_repos_directory(repos=[]):
        for repo in repos:
            repo.close()
            change_dir(os.path.dirname(repo.working_dir))
            time.sleep(1)
            try:
                shutil.rmtree(repo.working_dir,onerror=lambda func, path, _: (os.chmod(path, stat.S_IWRITE), func(path)))
            except PermissionError as err:
                print(f"Cannot delete {repo.working_dir}")
                raise err

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
