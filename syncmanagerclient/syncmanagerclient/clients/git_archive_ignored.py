from .git_base import GitClientBase
from ..util.syncconfig import SyncConfig

class GitArchiveIgnoredFiles(GitClientBase):

    def __init__(self, config : SyncConfig, gitrepo = None):
        super().__init__(gitrepo)
        if config:
            self.set_config(config)
            self.config = config

    def apply(self):
        raise NotImplementedError()