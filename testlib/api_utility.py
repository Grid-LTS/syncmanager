import urllib

from .testsetup import get_user_basic_authorization

get_clientenv_repos_url = f"/api/git/repos"

def headers(sync_user):
    return {"Authorization": get_user_basic_authorization(sync_user)}

def fetch_client_repo_from_api(client, client_env, sync_user):
    query_params = {
        "clientenv" : client_env,
        "full_info" : True
    }
    fetch_repo_list_resp = client.get(get_clientenv_repos_url + "?" + urllib.parse.urlencode(query_params), headers=headers(sync_user))
    return fetch_repo_list_resp.json()[0]