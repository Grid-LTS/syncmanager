from ..util.syncconfig import SyncConfig

class GitClientBase:

    def __init__(self, config : SyncConfig, gitrepo = None):
        self.gitrepo = gitrepo
        self.errors = []
        self.local_path_short = None
        self.local_path = None
        if config:
            self.set_config(config)

    def set_config(self, config : SyncConfig, *args):
        self.local_path_short = config.local_path_short
        self.local_path = config.local_path
        self.config = config

    def close(self):
        if self.gitrepo:
            self.gitrepo.close()
