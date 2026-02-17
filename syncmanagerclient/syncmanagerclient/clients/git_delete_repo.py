import os

import shutil
from .api import ApiService
from ..util.syncconfig import SyncConfig
from .git_base import GitClientBase


class GitRepoDeletion(GitClientBase):

    def __init__(self, config: SyncConfig, gitrepo=None):
        super().__init__(config, gitrepo)
        self.api_service = ApiService(config.mode, config.sync_env)

    def apply(self):
        self.initialize()
        print(f"Delete remote repo {self.gitrepo.remote}")
        if not self.config.remote_repo_info:
            print(f"Fetch server repo for local repo {self.local_path}")
            remote_repos = self.api_service.search_repos_by_namespace(self.config.namespace)
            if remote_repos:
                if len(remote_repos) == 1:
                    self.config.remote_repo_info = remote_repos[0]
                else:
                    print(f"Too many server repos registered for local repo {self.local_path}")
                    return
        if self.config.remote_repo_info:
            remote_repo_id = self.config.remote_repo_info["id"]
            self.api_service.delete_server_repo(remote_repo_id)
        print(f"Remove local repo {self.local_path}")
        try:
            if os.path.isdir(self.local_path):
                shutil.rmtree(self.local_path)
        except Exception as e:
            print(e)
            print(f"Cannot delete directory {self.local_path}")


    def get_remote_repo(self):
        try:
            return self.gitrepo.remote(self.config.remote_repo)
        except ValueError:
            return False
