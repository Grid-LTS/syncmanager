import os
from configparser import ConfigParser

from pathlib import Path

from .ArchiveConfig import ArchiveConfig
from .syncconfig import SyncAllConfig, GlobalConfig
from .system import sanitize_path



class Globalproperties:
    # this module encloses all globally accessible properties
    ini_path_prefix = ''
    conf_dir = ''
    var_dir = ''
    cache_dir:Path = None
    archive_dir_path: Path = None
    api_base_url = ''
    api_user = ''
    api_pw = ''
    ssh_user = ''
    ssh_host = ''
    test_mode = False
    loaded = False
    retention_years = None
    refresh_rate_months = None
    module_dir = ''
    archiveconfig = None
    allconfig = SyncAllConfig()
    offline = False

    @staticmethod
    def set_prefix(prefix):
        Globalproperties.ini_path_prefix = prefix

    @staticmethod
    def read_config(stage, organization=''):
        Globalproperties.loaded = True
        if stage == 'prod':
            properties_file_name = "server-sync.ini"
        else:
            properties_file_name = f"server-sync.{stage}.ini"
        properties_path = os.path.join(Globalproperties.ini_path_prefix, properties_file_name)
        config = ConfigParser()
        if not organization:
            organization = config.get('config', 'org_default', fallback='default')
        if os.path.isfile(properties_path):
            config.read(properties_path)
        else:
            message = f"Please create {properties_file_name} file in the project root {Globalproperties.ini_path_prefix}."
            if not Globalproperties.test_mode:
                print(message)
                exit(1)
            else:
                raise FileNotFoundError(message)
        Globalproperties.archiveconfig = ArchiveConfig(properties_path)
        Globalproperties.conf_dir = sanitize_path(config.get('config', 'conf_dir', fallback=None))
        if not Globalproperties.conf_dir:
            message = "Please specify the path to the config files in server-sync.ini."
            if not Globalproperties.test_mode:
                print(message)
                exit(1)
            else:
                raise RuntimeError(message)
        var_dir = config.get('config', 'var_dir', fallback=f"{os.path.expanduser('~')}/.syncmanager/var")
        if not var_dir:
            message = "Please specify the var_dir property in server-sync.ini."
            if not Globalproperties.test_mode:
                print(message)
                exit(1)
            else:
                raise RuntimeError(message)
        Globalproperties.var_dir = str(sanitize_path(var_dir))
        Globalproperties.archive_dir_relative = config.get('config', 'archive_dir_relative', fallback="archive")
        if Globalproperties.archive_dir_relative:
            Globalproperties.archive_dir_path = Path(Globalproperties.var_dir).joinpath(Globalproperties.archive_dir_relative)
            Globalproperties.archive_dir_path.mkdir(parents=True, exist_ok=True)
        Globalproperties.cache_dir = Path(Globalproperties.var_dir).joinpath("cache")
        Globalproperties.cache_dir.mkdir(parents=True, exist_ok=True)
        global_config = GlobalConfig(int(config.get('config', 'retention_years', fallback=2)),
                                     int(config.get('config', 'refresh_rate_months', fallback=6)))
        allconfig = Globalproperties.allconfig
        allconfig.global_config = global_config

        # determine sync environment
        if not os.environ.get('SYNC_ENV', None) and not config.get('config', 'SYNC_ENV', fallback=None):
            print("Please specify the environment with --env option or as SYNC_ENV in properties file. Using 'default'")
            config.set('config', 'SYNC_ENV', 'default')
        allconfig.sync_env = config.get('config', 'SYNC_ENV', fallback=None)
        if not allconfig.sync_env:
            allconfig.sync_env = os.environ.get('SYNC_ENV', None)
        Globalproperties.api_base_url = f"http://{config.get('server', 'API_HOST', fallback='')}" \
                       f":{config.get('server', 'API_PORT', fallback='5010')}/api"
        Globalproperties.api_user = config.get(f"org_{organization}", 'API_USER', fallback='')
        Globalproperties.api_pw = config.get(f"org_{organization}", 'API_PW', fallback='')
        Globalproperties.ssh_user = config.get('ssh', 'SSH_USER', fallback=None)
        Globalproperties.ssh_host = config.get('ssh', 'SSH_HOST', fallback=None)
        allconfig.username = config.get(f"git_{organization}", 'user_default', fallback=None)
        allconfig.email = config.get(f"git_{organization}", 'email_default', fallback=None)
        allconfig.organization = organization
