import os, shutil


import pytest

from .testsetup import USER_PASSWORD, get_admin_basic_authorization

@pytest.fixture(scope="module")
def client(app):
    return app.test_client()

@pytest.fixture(scope="module")
def runner(app):
    return app.app.test_cli_runner()

@pytest.fixture(scope="module")
def sync_api_user(client, request):
    body = {
        'username':  request.module.__name__.split(".")[-1],
        'password': USER_PASSWORD,
    }
    create_user_url = '/api/admin/user'
    headers = {"Authorization": get_admin_basic_authorization()}
    user_resp = client.post(create_user_url, json=body, headers=headers)
    assert user_resp.status_code == 200, "No admin user configured"
    user_obj= user_resp.json()
    return user_obj


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
                print(f"Cannot delete directory {path}")
