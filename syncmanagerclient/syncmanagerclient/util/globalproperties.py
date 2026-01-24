import os
from os.path import dirname
from configparser import ConfigParser

from pathlib import PurePosixPath,Path
import pathlib

from .ArchiveConfig import ArchiveConfig
from .baseconfig import GlobalConfig, SyncAllConfig
from .system import sanitize_path

class Globalproperties:
    # this module encloses all globally accessible properties
    conf_dir = ''
    var_dir = ''
    cache_dir: Path = None
    archive_dir_path: Path = None
    api_base_url = ''
    username = ''
    api_pw = ''
    ssh_user = ''
    ssh_host = ''
    test_mode = False
    loaded = False
    retention_years = None
    refresh_rate_months = None
    module_dir = dirname(dirname(os.path.abspath(__file__)))
    ini_path_prefix = dirname(module_dir)
    archiveconfig = None
    allconfig: SyncAllConfig = None
    config_parser = None
    organization = "default"
    sync_env_default = ''

    @staticmethod
    def set_prefix(prefix):
        Globalproperties.ini_path_prefix = prefix

    @classmethod
    def init_allconfig(cls, args):
        allconfig = SyncAllConfig(args)
        cls.allconfig = allconfig
        config_parser = cls.config_parser

        # determine sync environment
        if not os.environ.get('SYNC_ENV', None) and not config_parser.get('config', 'SYNC_ENV', fallback=None):
            print(f"Please specify the environment with --env option or as SYNC_ENV in properties file. Using '{cls.sync_env_default}'")
            config_parser.set('config', 'SYNC_ENV', cls.sync_env_default)
        allconfig.sync_env = config_parser.get('config', 'SYNC_ENV', fallback=None)
        if not allconfig.sync_env:
            allconfig.sync_env = os.environ.get('SYNC_ENV', None)
        allconfig.username = config_parser.get(f"git_{cls.organization}", 'user_default', fallback=None)
        allconfig.email = config_parser.get(f"git_{cls.organization}", 'email_default', fallback=None)
        allconfig.organization = cls.organization
        filesystem_root_dir = config_parser.get(f"sync_env_{allconfig.sync_env}","filesystem_root_dir",
                                                fallback=os.path.expanduser('~'))
        if filesystem_root_dir.endswith(':'):
            filesystem_root_dir += '/'
        global_config = GlobalConfig(filesystem_root_dir,
                                     int(config_parser.get('config', 'retention_years', fallback=2)),
                                     int(config_parser.get('config', 'refresh_rate_months', fallback=6)))
        allconfig.global_config = global_config

    @classmethod
    def read_config(cls, stage, organization=''):
        cls.loaded = True
        if stage == 'prod':
            properties_file_name = "server-sync.ini"
        else:
            properties_file_name = f"server-sync.{stage}.ini"
        properties_path = os.path.join(cls.ini_path_prefix, properties_file_name)
        cls.config_parser = ConfigParser()
        if not organization:
            organization = cls.config_parser.get('config', 'org_default', fallback='default')
        if os.path.isfile(properties_path):
            cls.config_parser.read(properties_path)
        else:
            message = f"Please create {properties_file_name} file in the project root {cls.ini_path_prefix}."
            if not cls.test_mode:
                print(message)
                exit(1)
            else:
                raise FileNotFoundError(message)
        cls.archiveconfig = ArchiveConfig(properties_path)
        cls.conf_dir = sanitize_path(cls.config_parser.get('config', 'conf_dir', fallback=None))
        if not cls.conf_dir:
            message = "Please specify the path to the config files in server-sync.ini."
            if not cls.test_mode:
                print(message)
                exit(1)
            else:
                raise RuntimeError(message)
        org_filesystem_root_dir = cls.config_parser.get(f"org_{organization}","filesystem_root_dir",
                                                    fallback=os.path.expanduser('~'))
        if org_filesystem_root_dir.endswith(':'):
            org_filesystem_root_dir += '/'
        var_dir = cls.config_parser.get('config', 'var_dir', fallback=f"~/.syncmanager/var")
        if not var_dir:
            message = "Please specify the var_dir property in server-sync.ini."
            if not cls.test_mode:
                print(message)
                exit(1)
            else:
                raise RuntimeError(message)
        if org_filesystem_root_dir:
            cls.var_dir = str(sanitize_path(var_dir, org_filesystem_root_dir))
        else:
            cls.var_dir = str(sanitize_path(var_dir))
        cls.archive_dir_relative = cls.config_parser.get('config', 'archive_dir_relative', fallback="archive")
        if cls.archive_dir_relative:
            cls.archive_dir_path = Path(cls.var_dir).joinpath(cls.archive_dir_relative)
            cls.archive_dir_path.mkdir(parents=True, exist_ok=True)
        cls.cache_dir = Path(cls.var_dir).joinpath("cache")
        cls.cache_dir.mkdir(parents=True, exist_ok=True)

        cls.api_base_url = f"http://{cls.config_parser.get('server', 'API_HOST', fallback='')}" \
                           f":{cls.config_parser.get('server', 'API_PORT', fallback='5010')}/api"
        cls.username = cls.config_parser.get(f"org_{organization}", 'API_USER', fallback='')
        cls.api_pw = cls.config_parser.get(f"org_{organization}", 'API_PW', fallback='')
        cls.sync_env_default = cls.config_parser.get(f"org_{organization}", 'sync_env_default', fallback='default')
        cls.ssh_user = cls.config_parser.get('ssh', 'SSH_USER', fallback=None)
        cls.ssh_host = cls.config_parser.get('ssh', 'SSH_HOST', fallback=None)



def determine_local_path_short(path) -> str:
    system_home_dir = Path(Globalproperties.allconfig.global_config.filesystem_root_dir)
    local_path_posix = PurePosixPath(path)
    if os.path.commonprefix([local_path_posix, system_home_dir]) == system_home_dir.as_posix():
        return '~/' + str(local_path_posix.relative_to(system_home_dir.as_posix()))
    else:
        return str(path)


def resolve_repo_path(path: str) -> Path:
    """
    Resolves a path to an absolute filesystem path.
    Handles ~ expansion and relative paths.
    :param path: Path string (relative, absolute, or with ~)
    :return: Absolute Path object
    """
    if not path.startswith('~'):
        return Path(path)
    posix = PurePosixPath(path)
    parts = list(posix.parts)
    if parts[0] == '~':
        parts[0] = Globalproperties.allconfig.global_config.filesystem_root_dir
    ret_path = pathlib.Path(*parts)
    return ret_path
