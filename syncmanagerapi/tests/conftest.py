import os
import sys

import pytest
import tempfile

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, project_dir)

from testlib.fixtures import empty_directory


sync_manager_server_conf = os.path.dirname(os.path.abspath(__file__))
var_dir_path = os.path.join("local", "var")
sync_base_dir_path = os.path.join(sync_manager_server_conf, var_dir_path)
git_base_dir_path = os.path.join(sync_base_dir_path, "git")


@pytest.fixture(scope="module")
def app():
    db_file_descriptor, db_path = tempfile.mkstemp()
    from syncmanagerapi import create_app
    app = create_app({
        'TESTING': True,
        'ENV': 'test',
        'DB_SQLITE_PATH': db_path,
        'SYNCMANAGER_SERVER_CONF': sync_manager_server_conf,
        'DB_RESET': True
    })
    yield app
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
    empty_directory(git_base_dir_path)

