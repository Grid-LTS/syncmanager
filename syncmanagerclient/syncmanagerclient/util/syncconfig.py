from __future__ import annotations

from pathlib import Path
import shutil

from .globalproperties import resolve_repo_path, determine_local_path_short



class SyncAllConfig:
    """
    SyncAllConfig is the static config given ini file and the run parameters provided on the command line
    The paramters here, different to Globalproperties, are dynamic, e.g. they can be set via command line parameters
    They can be overwritten by special config for the repos. Globalproperties cannot overwitten, they are fixed for all
    repos.
    """

    def __init__(self, args, sync_env=None, username=None, email=None, organization=None,
                 settings=None, global_config=None):
        self.args = args
        if sync_env:
            self.sync_env = sync_env
        else:
            self.sync_env = args.env
        self.username = username
        self.email = email
        self.organization = organization
        self.settings = settings
        self.global_config = global_config
        if args:
            self.offline = args.offline
            self.dry_run = args.dryrun
        else:
            self.offline = False
            self.dry_run = False


class SyncConfig(SyncAllConfig):
    """
    SyncConfig derives from and shares with SyncAllConfig because some of the static config in SyncAllConfig should be
    overwritten and configured dynamically via command line parameter
    """

    def __init__(self, args, mode, local_path_short=None, local_path: Path = None, remote_repo=None,
                 remote_repo_url=None,
                 namespace='', sync_env=None, username=None, email=None, organization=None,
                 settings=None, global_config=None):
        super().__init__(args, sync_env=sync_env, username=username, email=email, organization=organization,
                         settings=settings, global_config=global_config)
        self.remote_repo = remote_repo
        self.remote_repo_url = remote_repo_url
        self.remote_repo_info = None
        self._local_path_short = None
        self._local_path = None
        if namespace:
            self.namespace = namespace
        else:
            self.namespace = args.namespace
        if local_path_short:
            self.local_path_short = local_path_short
        if local_path:
            self.local_path = local_path
        if mode:
            self.mode = mode
        else:
            if args.client:
                self.mode = args.client
            else:
                self.mode = self.determine_mode()
        self.remote_repo_data = None
        self.default_branch = None

    @classmethod
    def init(cls, local_path_short=None, local_path: Path = None, remote_repo=None, remote_repo_url=None, namespace='',
             allconfig: SyncAllConfig = None):
        return cls(allconfig.args, allconfig.args.client, local_path_short=local_path_short, local_path=local_path,
                   remote_repo=remote_repo, remote_repo_url=remote_repo_url, namespace=namespace,
                   sync_env=allconfig.sync_env,
                   username=allconfig.username,
                   email=allconfig.email,
                   organization=allconfig.organization,
                   settings=allconfig.settings,
                   global_config=allconfig.global_config)

    @classmethod
    def from_sync_config(cls, other_config: SyncConfig):
        return cls(other_config.args, other_config.mode, local_path_short=other_config.local_path_short,
                   local_path=other_config.local_path,
                   remote_repo=other_config.remote_repo, remote_repo_url=other_config.remote_repo_url,
                   namespace=other_config.namespace, sync_env=other_config.sync_env, username=other_config.username,
                   email=other_config.email, organization=other_config.organization,
                   settings=other_config.settings, global_config=other_config.global_config)

    @property
    def local_path(self) -> Path:
        return self._local_path

    @property
    def local_path_short(self) -> str:
        return self._local_path_short

    @local_path.setter
    def local_path(self, path):
        if not isinstance(path, Path):
            path = resolve_repo_path(path)
        self._local_path_short = determine_local_path_short(path)
        self._local_path = path
        self.set_mode()

    @local_path_short.setter
    def local_path_short(self, value: str):
        if isinstance(value, Path):
            self._local_path_short = determine_local_path_short(value)
            self._local_path = value
        else:
            self._local_path_short = value
            self._local_path = resolve_repo_path(value)

    def set_mode(self):
        self.mode = self.determine_mode()

    def determine_mode(self):
        if not self.local_path:
            return ''
        if self.local_path.joinpath(".git").exists():
            return "git"
        return ''
