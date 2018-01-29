ACTION_PUSH = 'push'
ACTION_PULL = 'pull'
ACTION_SET_CONF = 'set_conf'
ACTION_SET_CONF_ALIASES = ['set_conf', 'set-conf', 'set-config', 'set_config']

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
