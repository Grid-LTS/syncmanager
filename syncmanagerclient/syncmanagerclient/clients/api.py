from xml.dom import InvalidStateErr

import requests as req
import json

from ..util.globalproperties import Globalproperties


class ApiService:

    def __init__(self, mode=None, sync_env=None):
        self.base_api_url = f"{Globalproperties.api_base_url}/{mode}"
        self.search_repos_url = f"{Globalproperties.api_base_url}/search/{mode}/repos"
        self.repos_base_url = f"{self.base_api_url}/repos"
        self.get_repos_by_clientenv_url = f"{self.base_api_url}/repos_by_clientenv"
        self.sync_env = sync_env
        self.auth = Globalproperties.api_user, Globalproperties.api_pw

    def search_repos_by_namespace(self, namespace):
        query_params = {
            "namespace": namespace,
            'full_info': True
        }
        repo_list = []
        for server_repo in self.list_repos(self.search_repos_url, query_params):
            server_repo = ApiService.retrieve_repo_reference(server_repo['userinfo'], self.sync_env)
            if not server_repo:
                continue
            repo_list.append(server_repo)
        return repo_list

    def list_repos_by_client_env(self, global_config, full=False):
        query_params = {
            "clientenv": self.sync_env,
            "retention_years": global_config.retention_years,
            "refresh_rate": global_config.refresh_rate_months,
            'full_info': full
        }
        return self.list_repos(self.repos_base_url, query_params)

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
            if Globalproperties.test_mode:
                raise ValueError(message)
            else:
                print(message)
                exit(1)
        if response.status_code >= 400 and response.status_code != 404:
            if Globalproperties.test_mode:
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
            'client_env': self.sync_env,
            'user_name_config': Globalproperties.allconfig.username,
            'user_email_config': Globalproperties.allconfig.email,
        }
        # optional fields
        if server_parent_path_relative:
            body['server_parent_dir_relative'] = server_parent_path_relative
        if repo_name:
            body['server_repo_name'] = repo_name
        body['all_client_envs'] = all_client_envs
        # create repo
        url = f"{self.base_api_url}/repos"
        resp = req.post(url, json=body, auth=self.auth)
        if resp.status_code == 500:
            raise InvalidStateErr(resp.text)
        return resp.json()

    def update_server_repo_client_repo_association(self, server_repo_id, local_path, server_path_rel):
        body = {
            'local_path': local_path,
            'server_path_rel': server_path_rel,
            'user_name_config': Globalproperties.allconfig.username,
            'user_email_config': Globalproperties.allconfig.email,
        }
        url = f"{self.base_api_url}/repos/{server_repo_id}/{self.sync_env}"
        response = req.put(url, json=body, auth=self.auth)
        ApiService.check_response(response, 200)
        git_repo = response.json()
        server_repo_ref = ApiService.retrieve_repo_reference(git_repo['userinfo'], self.sync_env)
        return git_repo, server_repo_ref

    def update_client_repo(self, payload):
        url = f"{self.base_api_url}/clientrepos/{payload["id"]}"
        response = req.put(url, json=payload, auth=self.auth)
        ApiService.check_response(response, 200)

    def add_client_env(self, client_env_name):
        body = {
            'client_env_name': client_env_name
        }
        url = f"{Globalproperties.api_base_url}/clientenv"
        return req.post(url, data=json.dumps(body), auth=self.auth)

    def update_server_repo(self, server_repo_id):
        url = f"{self.base_api_url}/repos/{server_repo_id}"
        return req.patch(url, data='{}', auth=self.auth)

    def delete_server_repo(self, server_repo_id):
        url = f"{self.base_api_url}/repos/{server_repo_id}"
        return req.delete(url, auth=self.auth)

    @staticmethod
    def check_response(response, desired_status_code):
        if response.status_code != desired_status_code:
            print(f"Error in processing. Received status {response.status_code} from server.")

    @staticmethod
    def retrieve_repo_reference(user_infos, sync_env):
        for user_info in user_infos:
            if sync_env in user_info['clientenvs']:
                server_repo_ref = user_info
                # existing reference found, abort lookup
                return server_repo_ref
        return None
