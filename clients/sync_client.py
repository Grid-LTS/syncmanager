from . import ACTION_PULL, ACTION_PUSH, ACTION_DELETE, ACTION_SET_CONF

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
            elif self.action in [ACTION_PUSH, ACTION_PULL, ACTION_DELETE]:
                return GitClientSync(self.action)
            else:
                raise Exception('Unknown command \'' + self.action + '\'.')
        else:
            # to be implemented
            print('unison')
            return None
