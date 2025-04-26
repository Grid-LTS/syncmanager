import os, shutil


import pytest

@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# can call CLIck commands
@pytest.fixture(scope="module")
def runner(app):
    return app.app.test_cli_runner()


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
