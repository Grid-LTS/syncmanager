import os
import pytest
import tempfile

from syncmanagerapi import create_app

sync_manager_server_conf = os.path.dirname(os.path.abspath(__file__))

app_singleton = None

@pytest.fixture(scope="module")
def app():
    global app_singleton
    db_file_descriptor, db_path = tempfile.mkstemp()
    if not app_singleton:
        app_singleton = create_app({
            'TESTING': True,
            'ENV': 'test',
            'DB_SQLITE_PATH': db_path,
            'SYNCMANAGER_SERVER_CONF': sync_manager_server_conf
        })
    yield app_singleton
    # tear down code
    os.close(db_file_descriptor)
    os.unlink(db_path)
    # Todo empty var directory


@pytest.fixture
def client(app):
    return app.test_client()


# can call CLIck commands
@pytest.fixture
def runner(app):
    return app.test_cli_runner()
