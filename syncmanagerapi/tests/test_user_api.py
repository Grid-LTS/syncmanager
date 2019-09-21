from setup import SYNC_ADMIN, SYNC_ADMIN_PASSWORD, create_admin, get_admin_basic_authorization


def test_unauthenticated(client, runner):
    create_admin(runner)
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
