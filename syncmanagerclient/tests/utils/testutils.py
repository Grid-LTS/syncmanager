import os

import shutil
import stat
import time
from pathlib import Path

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
get_other_repo_path = lambda repos_dir: build_local_repo_path(repos_dir, 'extra_ws')
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


def load_global_properties(stage="e2e", repos_root_dir=None):
    if not repos_root_dir:
        if not globalproperties.var_dir:
            raise ValueError("Your need configure 'var_dir' configuration parameter")
        prev_repos_dir = os.path.dirname(globalproperties.var_dir)
        prev_stage = os.path.basename(prev_repos_dir)
        if stage != prev_stage:
            repos_root_dir = os.path.join(os.path.dirname(prev_repos_dir), stage)
        else:
            repos_root_dir = prev_repos_dir
    else:
        stage = os.path.basename(repos_root_dir)
    var_dir = os.path.join(repos_root_dir, "var")
    Path(var_dir).mkdir(parents=True, exist_ok=True)
    init_global_properties(stage)
    globalproperties.set_prefix(os.path.dirname(test_dir))
    globalproperties.test_mode = True
    globalproperties.var_dir = var_dir

def build_local_repo_path(parent_dir, base):
    if not parent_dir:
        raise ValueError(f"Base dir for repos must not be empty")
    return os.path.join(parent_dir, base)

def teardown_repos_directory(repos=[]):
        for repo in repos:
            repo.close()
            teardown_repo_directory(repo.working_dir)

def teardown_repo_directory(working_dir):
    change_dir(os.path.dirname(working_dir))
    time.sleep(1)
    try:
        shutil.rmtree(working_dir,onerror=lambda func, path, _: (os.chmod(path, stat.S_IWRITE), func(path)))
    except PermissionError as err:
        print(f"Cannot delete {working_dir}")
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

def create_local_branch_from_remote(repo, local_branch, remote_branch):
    repo.create_head(local_branch, remote_branch)  # create local branch from remote
    if hasattr(repo.heads, str(local_branch)):
        getattr(repo.heads, str(local_branch)).set_tracking_branch(remote_branch)


def get_branch_name_and_repo_from_remote_path(remote_branch):
    remote_branch = remote_branch.strip()
    parts = remote_branch.split('/')
    return '/'.join(parts[1:]), parts[0]


def checkout_all_upstream_branches(repo, checkout_these_branches=[]):
    remote_repo = repo.remote('origin')
    for remote_ref in remote_repo.refs:
        name, remote_name = get_branch_name_and_repo_from_remote_path(str(remote_ref))
        if str(remote_ref) in checkout_these_branches and name != 'HEAD':
            print(f'Set up local tracking branch for {str(remote_ref)}')
            create_local_branch_from_remote(repo, name, remote_ref)