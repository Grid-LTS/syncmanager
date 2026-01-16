from .api import ApiService
from ..util.syncconfig import SyncConfig
from .git_base import GitClientBase



class GitRepoDeletion(GitClientBase):

    def __init__(self, config : SyncConfig, gitrepo = None):
        super().__init__(config, gitrepo)
        self.api_service = ApiService(config.mode, config.sync_env)


    def apply(self):
        self.initialize()
        print(f"Delete remote repo {self.gitrepo.remote}")
        remote_repo_id = self.config.remote_repo_info["id"]
        self.api_service.delete_server_repo(remote_repo_id)

    def get_remote_repo(self):
        try:
            return self.gitrepo.remote(self.config.remote_repo)
        except ValueError:
            return False