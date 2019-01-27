from . import ACTION_PULL, ACTION_PUSH, ACTION_DELETE, ACTION_SET_CONF

from .git_settings import GitClientSettings
from .git_sync import GitClientSync
from .unison_sync import UnisonClientSync


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
        elif self.mode == 'unison':
            # ACTION_PULL and ACTION_PUSH are the same in unison context
            return UnisonClientSync(self.action)
        else:
            print('Unknown client')
            return None
