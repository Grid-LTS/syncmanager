import requests as req
import json

import syncmanagerclient.util.globalproperties as globalproperties


class ApiService:

    def __init__(self, mode=None, sync_env=None):
        self.base_api_url = f"{globalproperties.api_base_url}/{mode}"
        self.get_repos_url = f"{self.base_api_url}/repos"
        self.get_repos_by_clientenv_url = f"{self.base_api_url}/repos_by_clientenv"
        self.sync_env = sync_env
        self.auth = globalproperties.api_user, globalproperties.api_pw

    def list_repos_by_client_env(self, full=False):
        query_params = {
            "clientenv" : self.sync_env,
            "retention_years" : 3,
            'full_info': full
        }
        return self.list_repos(self.get_repos_url, query_params)

    def list_repos_all_client_envs(self, full=False):
        url = self.get_repos_by_clientenv_url
        query_params = {
            'full_info': full
        }
        return self.list_repos(url, query_params)

    def list_repos(self, url, query_payload):
        response = req.get(url, params=query_payload, auth=self.auth)
        if response.status_code == 404:
            message = f"The sync environment '{self.sync_env}' is not registered on the server."
            if globalproperties.test_mode:
                raise ValueError(message)
            else:
                print(message)
                exit(1)
        if response.status_code >= 400 and response.status_code != 404:
            if globalproperties.test_mode:
                raise ValueError(response.text)
            else:
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
            body['server_repo_name'] = repo_name
        if all_client_envs:
            body['all_client_envs'] = all_client_envs
        # create repo
        url = f"{self.base_api_url}/repos"
        return req.post(url, json=body, auth=self.auth).json()

    def update_server_repo_reference(self, server_repo_id, local_path, server_path_rel):
        body = {
            'local_path': local_path,
            'server_path_rel': server_path_rel
        }
        url = f"{self.base_api_url}/repos/{server_repo_id}/{self.sync_env}"
        response = req.put(url, json=body, auth=self.auth)
        ApiService.check_response(response, 200)
        git_repo = response.json()
        server_repo_ref = ApiService.retrieve_repo_reference(git_repo['userinfo'], self.sync_env)
        return git_repo, server_repo_ref

    def add_client_env(self, client_env_name):
        body = {
            'client_env_name': client_env_name
        }
        url = f"{globalproperties.api_base_url}/clientenv"
        return req.post(url, data=json.dumps(body), auth=self.auth)

    def update_server_repo(self, server_repo_id):
        url = f"{self.base_api_url}/repos/{server_repo_id}"
        return req.patch(url, data='{}', auth=self.auth)

    @staticmethod
    def check_response(response, desired_status_code):
        if response.status_code != desired_status_code:
            print(f"Error in processing. Received status {response.status_code} from server.")

    @staticmethod
    def retrieve_repo_reference(user_info, sync_env):
        for user_info in user_info:
            referenced_envs = [env['env_name'] for env in user_info['client_envs']]
            if sync_env in referenced_envs:
                server_repo_ref = user_info
                # existing reference found, abort lookup
                return server_repo_ref
        return None
