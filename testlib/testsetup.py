from requests.auth import _basic_auth_str

SYNC_ADMIN = "syncman"
SYNC_ADMIN_PASSWORD = "pw1234"

USER = "eggs"
USER_PASSWORD = "secret"
USER_CLIENT_ENV = "integrationtest"
USER_CLIENT_ENV_DEFAULT = "default"
USER_CLIENT_ENV_EXTRA = "integrationtest-extra"

def create_admin(runner):
    runner.invoke(args=['admin-create', '--name', SYNC_ADMIN, '--password', SYNC_ADMIN_PASSWORD])


def get_admin_basic_authorization():
    # "Basic {user}".format(user=base64.b64encode(f"{SYNC_ADMIN}:{SYNC_ADMIN_PASSWORD}".encode()).decode())
    return _basic_auth_str(SYNC_ADMIN, SYNC_ADMIN_PASSWORD)

def get_user_basic_authorization(sync_user):
    return _basic_auth_str(sync_user["username"], sync_user["password"])



def create_client_env(client, env_name, sync_user):
    create_clientenv_url = "/api/clientenv"
    body = {
        'client_env_name': env_name
    }
    headers = {"Authorization": get_user_basic_authorization(sync_user)}
    client.post(create_clientenv_url, json=body, headers=headers)

def setup_users_and_env(client, sync_user):
    create_client_env(client, USER_CLIENT_ENV_DEFAULT, sync_user)
    create_client_env(client, USER_CLIENT_ENV, sync_user)
    create_client_env(client, USER_CLIENT_ENV_EXTRA, sync_user)

