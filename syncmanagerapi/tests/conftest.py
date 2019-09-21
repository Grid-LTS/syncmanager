import os
import pytest
import tempfile


from syncmanagerapi import create_app

sync_manager_server_conf = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def app():
    db_file_descriptor, db_path = tempfile.mkstemp()

    app = create_app({
        'TESTING': True,
        'ENV' : 'test',
        'DB_SQLITE_PATH': db_path,
        'SYNCMANAGER_SERVER_CONF' : sync_manager_server_conf
    })

    yield app
    os.close(db_file_descriptor)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

# can call CLIck commands
@pytest.fixture
def runner(app):
    return app.test_cli_runner()