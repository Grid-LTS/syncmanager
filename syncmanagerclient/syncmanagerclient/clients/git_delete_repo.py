from ..util.syncconfig import SyncConfig
from .git_base import GitClientBase



class GitRepoDeletion(GitClientBase):

    def __init__(self, config : SyncConfig, gitrepo = None):
        super().__init__(config, gitrepo)

    def apply(self):
        self.initialize()

    def get_remote_repo(self):
        try:
            return self.gitrepo.remote(self.config.remote_repo)
        except ValueError:
            return False