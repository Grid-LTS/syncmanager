import syncmanagerclient.util.globalproperties as globalproperties
import requests as req
import json


class ApiService:

    def __init__(self, mode, sync_env):
        self.base_api_url = f"{globalproperties.api_base_url}/{mode}"
        self.sync_env = sync_env

    def list_repos_by_client_id(self, full=False):
        url = f"{self.base_api_url}/repos/{self.sync_env}"
        query_payload = {'full_info': full}
        return req.get(url, params=query_payload, auth=(globalproperties.api_user, globalproperties.api_pw)).json()

    def create_remote_repository(self, local_path, server_parent_path_relative, repo_name, remote_name, client_id):
        body = {
            'local_path': local_path,
            'remote_name': remote_name,
            'client_id': client_id
        }
        # optional fields
        if server_parent_path_relative:
            body['server_parent_dir_relative'] = server_parent_path_relative
        if repo_name:
            body['repo_name'] = repo_name
        # create repo
        url = f"{self.base_api_url}/repos"
        return req.post(url, data=json.dumps(body), auth=(globalproperties.api_user, globalproperties.api_pw)).json()
