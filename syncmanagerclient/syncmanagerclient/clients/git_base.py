import os
from configparser import ConfigParser

from ..util.syncconfig import SyncConfig


class GitClientBase:

    def __init__(self, config : SyncConfig, gitrepo = None):
        self.gitrepo = gitrepo
        self.errors = []
        self.local_path_short = None
        self.local_path = None
        self.config = None
        if config:
            self.set_config(config)

    def set_config(self, config : SyncConfig, *args):
        self.local_path_short = config.local_path_short
        self.local_path = config.local_path
        self.config = config
        config_in_repo = os.path.join(self.local_path, 'syncmanager.ini')
        if os.path.exists(config_in_repo):
            config_parser = ConfigParser()
            config_parser.read(config_in_repo)
            self.config.organization = config_parser.get('config', 'org_default', fallback=config.organization)


    def close(self):
        if self.gitrepo:
            self.gitrepo.close()
