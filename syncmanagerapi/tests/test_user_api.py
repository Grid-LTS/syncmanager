import os
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, project_dir)

from testlib.testsetup import create_admin, get_admin_basic_authorization

def test_create_user(initialized_app, client):
    body = {
        'username': 'john',
        'password': 'lennon123',
    }
    create_user_url = '/api/admin/user'
    response = client.post(create_user_url, json=body)
    assert response.status_code == 401
    headers = {"Authorization": get_admin_basic_authorization()}
    response = client.post(create_user_url, json=body, headers=headers)
    assert response.status_code == 200
