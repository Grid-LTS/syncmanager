import os

from . import ACTION_PULL, ACTION_PUSH, ACTION_SET_CONF, ACTION_SET_CONF_ALIASES, ACTION_DELETE

from .git_settings import GitClientSettings
from .git_sync import GitClientSync


class SyncClientFactory:
    def __init__(self, mode, action):
        self.mode = mode
        self.action = action

    def get_instance(self):
        if self.mode == 'git':
            if self.action == ACTION_SET_CONF:
                return GitClientSettings()
            elif self.action in [ACTION_PUSH, ACTION_PULL]:
                return GitClientSync(self.action)
            else:
                raise Exception('Unknown command \'' + self.action + '\'.')
        else:
            print('unison')
            return None


class DeletionRegistration:
    def __init__(self, path):
        self.path = path

    def get_mode(self):
        # first check if directory is a git working tree
        current_dir = os.getcwd()
        if os.path.isdir(current_dir + '/.git'):
            return 'git'
        #to be implemented: Unison check for
        return None

    def register_path(self):
        mode = self.get_mode()
        pass