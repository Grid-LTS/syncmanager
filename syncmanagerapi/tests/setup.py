from requests.auth import _basic_auth_str

SYNC_ADMIN = "syncman"
SYNC_ADMIN_PASSWORD = "pw1234"


def create_admin(runner):
    result = runner.invoke(args=['admin-create', '--name', SYNC_ADMIN, '--password', SYNC_ADMIN_PASSWORD])
    assert f"Created user {SYNC_ADMIN}" in result.output


def get_admin_basic_authorization():
    # "Basic {user}".format(user=base64.b64encode(f"{SYNC_ADMIN}:{SYNC_ADMIN_PASSWORD}".encode()).decode())
    return _basic_auth_str(SYNC_ADMIN, SYNC_ADMIN_PASSWORD)
