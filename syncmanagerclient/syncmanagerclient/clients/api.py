import syncmanagerclient.util.globalproperties as globalproperties
import requests as req
import json


class ApiService:

    def __init__(self, mode=None, sync_env=None):
        self.base_api_url = f"{globalproperties.api_base_url}/{mode}"
        self.get_repos_url = f"{self.base_api_url}/repos"
        self.sync_env = sync_env
        self.auth = globalproperties.api_user, globalproperties.api_pw

    def list_repos_by_client_env(self, full=False):
        url = f"{self.base_api_url}/repos/{self.sync_env}"
        return self.list_repos(url, full)

    def list_repos_all_client_envs(self, full=False):
        url = self.get_repos_url
        return self.list_repos(url, full)

    def list_repos(self, url, full=False):
        url = f"{self.base_api_url}/repos"
        query_payload = {'full_info': full}
        response = req.get(url, params=query_payload, auth=self.auth)
        if response.status_code == 404:
            print(f"The sync environment '{self.sync_env}' is not registered on the server.")
            exit(1)
        if response.status_code >= 400 and response.status_code != 404:
            print(f"{response.text}")
            exit(1)
        if not response.json():
            return []
        return response.json()

    def create_remote_repository(self, local_path, server_parent_path_relative, repo_name, remote_name,
                                 all_client_envs=False):
        body = {
            'local_path': local_path,
            'remote_name': remote_name,
            'client_env': self.sync_env
        }
        # optional fields
        if server_parent_path_relative:
            body['server_parent_dir_relative'] = server_parent_path_relative
        if repo_name:
            body['repo_name'] = repo_name
        if all_client_envs:
            body['all_client_envs'] = all_client_envs
        # create repo
        url = f"{self.base_api_url}/repos"
        return req.post(url, data=json.dumps(body), auth=self.auth).json()

    def add_client_env(self, client_env_name):
        body = {
            'client_env_name': client_env_name
        }
        url = f"{globalproperties.api_base_url}/clientenv"
        return req.post(url, data=json.dumps(body), auth=self.auth)
