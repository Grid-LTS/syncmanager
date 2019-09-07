from jinja2 import Environment, FileSystemLoader
from git import Repo
import os
import shutil
from pathlib import Path

# Project files
from syncmanagerclient.main import apply_sync_conf_files, register_local_branch_for_deletion
from syncmanagerclient.clients import ACTION_PULL, ACTION_PUSH
import syncmanagerclient.util.globalproperties as globalproperties

test_dir =  os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
test_user_email = 'dummy@test.com'

TEMPLATE_ENVIRONMENT = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(test_dir, 'templates')),
        trim_blocks=False)


def detemplate_conf(sync_env, context):
    conf_file = TEMPLATE_ENVIRONMENT.get_template('{}.conf.j2'.format(sync_env)).render(context)
    conf_file_name = '{}.conf'.format(sync_env)
    f = open(os.path.join(test_dir, conf_file_name), 'w')
    f.write(conf_file)
    f.close()


def detemplate_properties(context):
    server_properties = TEMPLATE_ENVIRONMENT.get_template('server-sync.test.properties.j2').render(context)
    f = open(os.path.join(os.path.dirname(test_dir), 'server-sync.test.properties'), 'w')
    f.write(server_properties)
    f.close()


def setup_repos(local_conf_file_name):
    context = {
        'local_path': local_repo_path,
        'others_path': others_repo_path,
        'origin_path': origin_repo_path,
        'test_user_name': test_user_name,
        'test_user_email': test_user_email

    }
    for sync_env in ['local', 'others']:
        detemplate_conf(sync_env, context)
    # detemplatize server-sync properties
    context = {
        'config_files_path': test_dir,
        'var_dir_path': var_dir_path
    }
    detemplate_properties(context)
    # setup global properties file
    globalproperties.set_prefix(os.path.dirname(test_dir))
    globalproperties.read_config('test')
    repos_dir = os.path.join(test_dir, 'repos')
    shutil.rmtree(repos_dir, ignore_errors=True)
    if not os.path.exists(repos_dir):
        os.mkdir(repos_dir)
        # setup repos
    origin_repo = Repo.init(origin_repo_path, bare=True)
    local_repo = Repo.init(local_repo_path)
    local_repo.create_remote('origin', url=os.path.abspath(origin_repo.working_dir))
    # add origin_repo as remote
    # create file and commit
    test_file_path = os.path.join(local_repo_path, 'file.txt')
    Path(test_file_path).touch()
    local_repo.index.add([test_file_path])
    local_repo.index.commit("Initial commit on master branch")
    apply_sync_conf_files(test_dir, [local_conf_file_name], ACTION_PUSH, False, '', ['git'])
    return origin_repo, local_repo
