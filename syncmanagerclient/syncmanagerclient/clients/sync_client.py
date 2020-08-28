import pathlib

from . import ACTION_PULL, ACTION_PUSH, ACTION_DELETE, ACTION_SET_CONF

from .git_settings import GitClientSettings
from .git_sync import GitClientSync
from .sync_dir_registration import SyncDirRegistration
from .unison_sync import UnisonClientSync

import syncmanagerclient.util.globalproperties as globalproperties

from .api import ApiService


class SyncClient:

    def __init__(self, mode, action, sync_env=None, force=False, namespace=None):
        self.mode = mode
        self.action = action
        if sync_env:
            self.sync_env = sync_env
        else:
            self.sync_env = globalproperties.sync_env
        self.force = force
        self.namespace = namespace
        self.errors = []

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

    def sync_with_remote_repo(self, config):
        client_instance = self.get_instance()
        if not client_instance:
            return
        client_instance.set_config(config, self.force)
        client_instance.apply()
        if client_instance.errors:
            self.errors.extend(client_instance.errors)

    def get_and_sync_repos(self):
        api_service = ApiService(self.mode, self.sync_env)
        remote_repos = api_service.list_repos_by_client_env(full=True)
        if self.namespace:
            print(f"Only syncing repos in namespace {self.namespace}")
        for remote_repo in remote_repos:
            if self.namespace:
                p_ns = pathlib.Path(self.namespace)
                p = pathlib.Path(remote_repo['git_repo']['server_path_rel'])
                p = pathlib.Path(*p.parts[1:])
                if not str(p).startswith(str(p_ns)):
                    continue
            config = {
                'source': remote_repo['local_path_rel'],
                'remote_repo': remote_repo['remote_name'],
                'url': SyncDirRegistration.get_remote_url(remote_repo['git_repo']['server_path_absolute'])
            }
            self.sync_with_remote_repo(config)
        if self.errors:
            print('')
            print('#####################################################################################')
            print('Following repositories could not be (completely) synced:')
            print('')
            for error in self.errors:
                print(f"{error.local_repo_path}")
                print(f"Context: {error.context}")
                print("Error message:")
                print(error.error)
                print('-------------------------------------------------------------------------------------')
                print('')
