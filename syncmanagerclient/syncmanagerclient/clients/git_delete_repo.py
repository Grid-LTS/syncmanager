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

    def get_remote_repo(self):
        try:
            return self.gitrepo.remote(self.config.remote_repo)
        except ValueError:
            return False