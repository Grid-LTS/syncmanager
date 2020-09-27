import os, shutil
import pytest
import tempfile

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
    # tear down code
    os.close(db_file_descriptor)
    os.unlink(db_path)
    empty_directory(git_base_dir_path)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# can call CLIck commands
@pytest.fixture(scope="module")
def runner(app):
    return app.test_cli_runner()


def empty_directory(path):
    if os.path.isdir(path):
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(e)
                assert False, f"Cannot delete directory {path}"
