import os
import pytest

from .utils.testutils import local_conf_file_name, test_dir
from .utils.conffileutils import setup_repos, teardown_repos_directory, detemplate_conf
from syncmanagerclient.main import apply_sync_conf_files
from syncmanagerclient.clients import ACTION_SET_CONF

@pytest.fixture(scope="module")
def setup_git_repos(request):
    # Set up the repositories before tests
    origin_repo, local_repo = setup_repos(local_conf_file_name, request.module.__name__.split(".")[-1])
    yield origin_repo, local_repo
    teardown_repos_directory([origin_repo, local_repo])

def test_set_config(setup_git_repos):
    origin_repo, local_repo = setup_git_repos

    mod_user_name = 'Mod User'
    mod_user_email = 'foobaz@tests.com'
    mod_origin_path = os.path.join(os.path.dirname(origin_repo.working_dir), 'dummy_repo')
    context = {
        'local_path': local_repo.working_dir,
        'origin_path': mod_origin_path,
        'mod_user_name': mod_user_name,
        'mod_user_email': mod_user_email
    }
    mod_env = 'localmod'
    detemplate_conf(mod_env, context)
    apply_sync_conf_files(test_dir, [mod_env + '.conf'], ACTION_SET_CONF, False, '', ['git'])

    conf_reader = local_repo.config_reader()
    assert conf_reader.get_value('user', 'name') == mod_user_name

    # Check that remote repo url was modified as well
    remote_repo = local_repo.remote('origin')
    conf_reader_remote = remote_repo.config_reader
    assert conf_reader_remote.get_value("url")[7:] == mod_origin_path
