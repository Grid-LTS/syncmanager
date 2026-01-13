import os
import sys
import tempfile
import time
from threading import Thread

from git import Repo

import pytest


from syncmanagerclient.main import execute_command
from syncmanagerclient.util.syncconfig import SyncConfig

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
e2e_test_workspace_root = os.path.join(test_dir, "repos")
if not project_dir in sys.path:
    sys.path.insert(0, project_dir)

from .utils.testutils import *

from testlib.testsetup import USER_CLIENT_ENV, setup_users_and_env, get_user_basic_authorization, create_admin
from testlib.fixtures import empty_directory, sync_api_user


"""
Define fixtures only here. DO NOT import any fixture functions into the test_* classes !!
"""
@pytest.fixture(scope="module")
def init_test(sync_api_user):
    """
    to be overwritten in the test modules by redeclaration
    """
    pass


def setup_local_repo(sync_user, repo_name):
    # stage is not to be confused with sync env. we don't have the possiblity of test with a physically different
    # environment so we introduce another stage that allows us to configure a different environment/machine
    stage = "e2e"
    repos_root_dir = os.path.join(e2e_test_workspace_root, repo_name, stage)
    shutil.rmtree(repos_root_dir, ignore_errors=True, onerror=lambda func, path, _: (os.chmod(path, stat.S_IWRITE),
                                                                                func(path)))
    if not os.path.exists(repos_root_dir):
        Path(repos_root_dir).mkdir(parents=True)
    local_repo_path = get_local_repo_path(repos_root_dir)
    local_repo = Repo.init(local_repo_path)
    change_dir(local_repo_path)
    # create file and commit
    test_file_path = os.path.join(local_repo_path, 'file.txt')
    Path(test_file_path).touch()
    local_repo.index.add([test_file_path])
    local_repo.index.commit("Initial commit on principal branch")
    Globalproperties.api_user = sync_user["username"]
    Globalproperties.api_pw = sync_user["password"]
    args = ArgumentsTest()
    args.action = "set-remote"
    args.force = False
    args.env = ''
    args.offline = False
    args.dryrun = False
    if not Globalproperties.allconfig:
        Globalproperties.init_allconfig(args)
    sync_config = SyncConfig.init(allconfig = Globalproperties.allconfig)
    execute_command(args, sync_config, remote_name = "origin")
    return local_repo


@pytest.fixture(scope="package")
def app():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(test_dir))
    syncmanagerapi_dir = os.path.join(project_dir, "syncmanagerapi")
    sys.path.insert(0, syncmanagerapi_dir)
    db_file_descriptor, db_path = tempfile.mkstemp()
    from syncmanagerapi import create_app
    app = create_app({
        'ENV': 'e2e',
        'DB_SQLITE_PATH': db_path,
        'SYNCMANAGER_SERVER_CONF': syncmanagerapi_dir,
        'DB_RESET': True,
        'SERVER_PORT': 8010
    })
    thread = Thread(target=app.run, daemon=True, kwargs=dict(host='localhost', port=8010))
    thread.start()
    yield app
    git_base_dir_path = app.app.config["FS_ROOT"]
    with app.app.app_context():
        db_instance = app.app.extensions["sqlalchemy"]
        db_instance.session.close()
        db_instance.engine.dispose()
    # tear down code
    try:
        os.close(db_file_descriptor)
        os.unlink(db_path)
    except PermissionError as perm:
        print(f"Database file could not be cleaned up")
        raise perm
    time.sleep(1)
    empty_directory(git_base_dir_path)


# can call CLIck commands
@pytest.fixture(scope="package")
def runner(app):
    return app.app.test_cli_runner()


@pytest.fixture(scope="package")
def client(app):
    return app.test_client()


@pytest.fixture(scope="package")
def app_initialized(app, runner):
    create_admin(runner)
    return app


@pytest.fixture(scope="module")
def local_repo(init_test, client, sync_api_user):
    user = sync_api_user
    setup_users_and_env(client, user)
    local_repo = setup_local_repo(user,  sync_api_user["username"])
    yield local_repo
    teardown_repos_directory([local_repo])
    other_repo_path = get_other_repo_path(os.path.join(e2e_test_workspace_root, sync_api_user["username"], 'e2e-extra'))
    if os.path.exists(other_repo_path):
        teardown_repo_directory(other_repo_path)

