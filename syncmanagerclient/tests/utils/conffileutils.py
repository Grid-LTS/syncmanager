from jinja2 import Environment, FileSystemLoader
from git import Repo

from pathlib import Path


# Project files
from syncmanagerclient.main import apply_sync_conf_files
from syncmanagerclient.clients import ACTION_PUSH
import syncmanagerclient.util.globalproperties as globalproperties

from .testutils import *


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
    server_properties = TEMPLATE_ENVIRONMENT.get_template('server-sync.test.ini.j2').render(context)
    f = open(os.path.join(os.path.dirname(test_dir), 'server-sync.test.ini'), 'w')
    f.write(server_properties)
    f.close()


def setup_repos(local_conf_file_name, repo_prefix):
    if not repo_prefix:
        raise ValueError(f"Base dir for repos must not be empty")
    repos_dir = os.path.join(test_dir, 'repos', repo_prefix)
    local_repo_path = get_local_repo_path(repos_dir)
    origin_repo_path = get_origin_repo_path(repos_dir)
    others_repo_path = get_others_repo_path(repos_dir)
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

    shutil.rmtree(repos_dir, ignore_errors=True, onerror=lambda func, path, _: (os.chmod(path, stat.S_IWRITE), func(path)))
    if not os.path.exists(repos_dir):
        os.makedirs(repos_dir)
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


