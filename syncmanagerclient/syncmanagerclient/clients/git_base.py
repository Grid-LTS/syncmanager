import os
from configparser import ConfigParser

from ..util.system import change_dir
from .error import GitSyncError, GitErrorItem
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

    def change_to_local_repo(self):
        # first check if the local repo exists and is a git working space
        repo_exists = os.path.isdir(self.local_path)
        print('Change to Git project \'{0}\'.'.format(self.local_path_short))
        if os.path.isdir(os.path.join(self.local_path, '.git')):
            ret_val = change_dir(self.local_path)
            if ret_val != 0:
                print('Cannot change to repository \'{0}\'.'.format(self.local_path))
            return ret_val
        elif repo_exists:
            message = f"The repository '{self.local_path}' exists, but is not a git repository"
            error = GitSyncError(message)
            self.errors.append(
                GitErrorItem(self.local_path_short, error, "git clone")
            )
            print(message)
            return 1

