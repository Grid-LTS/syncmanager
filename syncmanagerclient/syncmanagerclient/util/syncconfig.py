from __future__ import annotations
import os.path as osp

from pathlib import PurePosixPath, Path
from ..util.system import sanitize_posix_path, home_dir


class GlobalConfig:
    def __init__(self, retention_years=None, refresh_rate_months=None):
        self.retention_years = retention_years
        self.refresh_rate_months = refresh_rate_months


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

    def __init__(self, args, local_path_short=None, local_path: Path = None, remote_repo=None, remote_repo_url=None,
                 namespace='', sync_env=None, username=None, email=None, organization=None,
                 settings=None, global_config=None):
        super().__init__(args, sync_env=sync_env, username=username, email=email, organization=organization,
                         settings=settings, global_config=global_config)
        self.remote_repo = remote_repo
        self.remote_repo_url = remote_repo_url
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

    @classmethod
    def init(cls, local_path_short=None, local_path: Path = None, remote_repo=None, remote_repo_url=None, namespace='',
             allconfig: SyncAllConfig = None):
                         return cls(allconfig.args, local_path_short=local_path_short, local_path=local_path, remote_repo=remote_repo,
                   remote_repo_url=remote_repo_url, namespace=namespace,
                   sync_env=allconfig.sync_env,
                   username=allconfig.username,
                   email=allconfig.email,
                   organization=allconfig.organization,
                   settings=allconfig.settings,
                   global_config=allconfig.global_config)

    @classmethod
    def from_sync_config(cls, other_config: SyncConfig):
        return cls(other_config.args, local_path_short=other_config.local_path_short,
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
        path = sanitize_posix_path(path)
        self._local_path_short = SyncConfig.determine_local_path_short(path)
        self._local_path = path

    @local_path_short.setter
    def local_path_short(self, value: str):
        if isinstance(value, Path):
            self._local_path_short = SyncConfig.determine_local_path_short(value)
            self._local_path = value
        else:
            self._local_path_short = value
            self._local_path = sanitize_posix_path(value)

    @staticmethod
    def determine_local_path_short(path):
        system_home_dir = PurePosixPath(Path(home_dir))
        local_path_posix = PurePosixPath(path)
        if osp.commonprefix([local_path_posix, system_home_dir]) == system_home_dir.as_posix():
            return '~/' + str(local_path_posix.relative_to(system_home_dir).as_posix())
        else:
            return str(path)
