import json
import os.path

from git import Repo

from . import ACTION_PULL, ACTION_PUSH, ACTION_DELETE, ACTION_SET_CONF_ALIASES, \
    ACTION_ARCHIVE_IGNORED_FILES, ACTION_INIT_REPO, ACTION_DELETE_REPO
from .api import ApiService
from .git_archive_ignored import GitArchiveIgnoredFiles
from .git_delete_repo import GitRepoDeletion
from .git_init_repo import GitInitRepo
from .git_settings import GitClientSettings
from .git_sync import GitClientSync
from .sync_dir_registration import SyncDirRegistration
from .unison_sync import UnisonClientSync
from ..util.error import InvalidArgument
from ..util.globalproperties import Globalproperties
from ..util.syncconfig import SyncConfig


class SyncClient:

    def __init__(self, action, sync_config: SyncConfig = None, force=False):
        self.action = action
        if sync_config and sync_config.sync_env:
            self.sync_env = sync_config.sync_env
        else:
            self.sync_env = Globalproperties.allconfig.sync_env
        self.force = force
        self.errors = []
        self.is_update = False

        self.sync_config = sync_config
        if not self.sync_config.mode:
            raise InvalidArgument(f"Sync client cannot be determined or is not supported")
        self.api_service = ApiService(self.sync_config.mode, self.sync_env)

    def get_instance(self, config: SyncConfig = None):
        if self.sync_config.mode == 'git':
            if self.action in ACTION_SET_CONF_ALIASES:
                return GitClientSettings(config)
            elif self.action in [ACTION_PUSH, ACTION_PULL, ACTION_DELETE]:
                self.is_update = True
                return GitClientSync(self.action, config, force=self.force)
            elif self.action == ACTION_ARCHIVE_IGNORED_FILES:
                return GitArchiveIgnoredFiles(config)
            elif self.action == ACTION_INIT_REPO:
                return GitInitRepo(config)
            elif self.action == ACTION_DELETE_REPO:
                return GitRepoDeletion(config)
            else:
                raise Exception('Unknown command \'' + self.action + '\'.')
        elif self.sync_config.mode == 'unison':
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
        """
        should be more abstract. so far this code is Git specific
        :param sync_config:
        :return:
        """
        if self.sync_config.namespace:
            print(f"Only syncing repos in namespace {self.sync_config.namespace}")
        remote_repos = self.fetch_repos(self.sync_config)
        for remote_repo in remote_repos:
            config = self.update_config(self.sync_config, remote_repo)
            self.sync_with_remote_repo(config)
            if not self.is_update:
                continue
            self.api_service.update_server_repo(remote_repo['git_repo']['id'])
            if "user_name_config" in remote_repo and not remote_repo["user_name_config"] \
                    or "user_email_config" in remote_repo and not remote_repo["user_email_config"]:
                remote_repo["user_name_config"] = config.username
                remote_repo["user_email_config"] = config.email
                print(f"Update config on server and locally.")
                self.api_service.update_client_repo(remote_repo)
                sync_settings = GitClientSettings(config)
                sync_settings.set_user_config()
                if sync_settings.errors:
                    self.errors.extend(sync_settings.errors)
        self.report_errors()

    def sync_single_repo(self):
        if self.sync_config.mode != "git":
            print("No sync client beside git is supported")
            return
        repo = Repo(self.sync_config.local_path)
        remote_repo = None
        for remote_repo_name in repo.remotes:
            remote = repo.remote(remote_repo_name)
            if 'syncmanager' in repo.remote(remote_repo_name).url:
                remote_repo = remote
                break
        segments = remote_repo.url.split(os.path.sep)
        self.sync_config.namespace = os.path.sep.join(segments[segments.index("git") + 1:])
        remote_repos = self.fetch_repos(self.sync_config)
        for remote_repo in remote_repos:
            config = self.update_config(self.sync_config, remote_repo)
            self.sync_with_remote_repo(config)
        self.report_errors()

    def fetch_repos(self, sync_config: SyncConfig):
        if sync_config.namespace:
            return self.api_service.search_repos_by_namespace(sync_config.namespace)
        cache_repose_path = Globalproperties.cache_dir.joinpath("remote_repos.json")
        cache_disabled = Globalproperties.test_mode
        remote_repos = []
        if not sync_config.offline or cache_disabled:
            remote_repos = self.api_service.list_repos_by_client_env(sync_config.global_config, full=True)
            if remote_repos and not cache_disabled:
                with cache_repose_path.open("w", encoding="utf-8") as f:
                    json.dump(remote_repos, f, ensure_ascii=False, indent=2)
        else:
            with cache_repose_path.open("r", encoding="utf-8") as f:
                remote_repos = json.load(f)
        return remote_repos

    def update_config(self, sync_config, remote_repo):
        config = SyncConfig.from_sync_config(sync_config)
        config.local_path = remote_repo['local_path_rel']
        config.remote_repo = remote_repo['remote_name']
        config.remote_repo_url = SyncDirRegistration.get_remote_url(
            remote_repo['git_repo']['server_path_absolute'])
        config.username = remote_repo["user_name_config"] if remote_repo["user_name_config"] else config.username
        config.email = remote_repo["user_email_config"] if remote_repo["user_email_config"] else config.email
        config.remote_repo_info =  remote_repo['git_repo']
        return config

    def report_errors(self):
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

