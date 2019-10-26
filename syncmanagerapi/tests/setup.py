from requests.auth import _basic_auth_str

SYNC_ADMIN = "syncman"
SYNC_ADMIN_PASSWORD = "pw1234"

USER = "eggs"
USER_PASSWORD = "secret"
USER_CLIENT_ENV = "intregationtest"


def create_admin(runner):
    runner.invoke(args=['admin-create', '--name', SYNC_ADMIN, '--password', SYNC_ADMIN_PASSWORD])


def get_admin_basic_authorization():
    # "Basic {user}".format(user=base64.b64encode(f"{SYNC_ADMIN}:{SYNC_ADMIN_PASSWORD}".encode()).decode())
    return _basic_auth_str(SYNC_ADMIN, SYNC_ADMIN_PASSWORD)


def get_user_basic_authorization():
    return _basic_auth_str(USER, USER_PASSWORD)


def create_user(client):
    body = {
        'username': USER,
        'password': USER_PASSWORD,
    }
    create_user_url = '/api/admin/user'
    headers = {"Authorization": get_admin_basic_authorization()}
    client.post(create_user_url, json=body, headers=headers)


def create_client_env(client):
    create_clientenv_url = "/api/clientenv"
    body = {
        'client_env_name': "intregationtest"
    }
    headers = {"Authorization": get_user_basic_authorization()}
    client.post(create_clientenv_url, json=body, headers=headers)


def setup_users_and_env(client, runner):
    create_admin(runner)
    create_user(client)
    create_client_env(client)
