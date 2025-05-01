import pathlib

from . import ACTION_PULL, ACTION_PUSH, ACTION_DELETE, ACTION_SET_CONF_ALIASES

from .git_settings import GitClientSettings
from .git_sync import GitClientSync
from .sync_dir_registration import SyncDirRegistration
from .unison_sync import UnisonClientSync

import syncmanagerclient.util.globalproperties as globalproperties
from syncmanagerclient.util.syncconfig import SyncConfig

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
        self.is_update = False

    def get_instance(self, config: SyncConfig = None):
        if self.mode == 'git':
            if self.action in ACTION_SET_CONF_ALIASES:
                return GitClientSettings(config)
            elif self.action in [ACTION_PUSH, ACTION_PULL, ACTION_DELETE]:
                self.is_update = True
                return GitClientSync(self.action, config, force=self.force)
            else:
                raise Exception('Unknown command \'' + self.action + '\'.')
        elif self.mode == 'unison':
            # ACTION_PULL and ACTION_PUSH are the same in unison context
            return UnisonClientSync(self.action)
        else:
            print('Unknown client')
            return None

    def sync_with_remote_repo(self, config: SyncConfig):
        """
        config obj corresponds to local instance (aka local repo), it contains all information necessary for syncing
        :param config:
        :return:
        """
        client_instance = self.get_instance(config)
        if not client_instance:
            return
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
            config = SyncConfig.init(allconfig=globalproperties.allconfig)
            config.local_path = remote_repo['local_path_rel']
            config.remote_repo = remote_repo['remote_name']
            config.remote_repo_url = SyncDirRegistration.get_remote_url(
                remote_repo['git_repo']['server_path_absolute'])
            config.username = remote_repo["user_name_config"]  if remote_repo["user_name_config"]   else config.username
            config.email = remote_repo["user_email_config"]  if remote_repo["user_email_config"]   else config.email
            self.sync_with_remote_repo(config)
            if self.is_update:
                api_service.update_server_repo(remote_repo['git_repo']['id'])
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
