import os
from configparser import ConfigParser

from .gitconfig import GitConfig

# this module encloses all globally accessible properties
ini_path_prefix = ''
conf_dir = ''
sync_env = ''
var_dir = ''
api_base_url = ''
api_user = ''
api_pw = ''
ssh_user = ''
ssh_host = ''
test_mode = False



gitconfig = GitConfig()


def set_prefix(prefix):
    global ini_path_prefix
    ini_path_prefix = prefix


def read_config(stage, organization=''):
    global ini_path_prefix
    global conf_dir
    global sync_env
    global var_dir
    global api_base_url
    global api_user
    global api_pw
    global ssh_user
    global ssh_host
    global test_mode
    if stage == 'prod':
        properties_file_name = "server-sync.ini"
    else:
        properties_file_name = f"server-sync.{stage}.ini"
    properties_path = os.path.join(ini_path_prefix, properties_file_name)
    config = ConfigParser()
    if not organization:
        organization = config.get('config', 'org_default', fallback='default')
    if os.path.isfile(properties_path):
        config.read(properties_path)
    else:
        message = f"Please create {properties_file_name} file in the project root {ini_path_prefix}."
        if not test_mode:
            print(message)
            exit(1)
        else:
            raise FileNotFoundError(message)
    conf_dir = config.get('config', 'conf_dir', fallback=None)
    if not conf_dir:
        message= "Please specify the path to the config files in server-sync.ini."
        if not test_mode:
            print(message)
            exit(1)
        else:
            raise RuntimeError(message)
    var_dir = config.get('config', 'var_dir', fallback=None)
    if not var_dir:
        message = "Please specify the var_dir property in server-sync.ini."
        if not test_mode:
            print(message)
            exit(1)
        else:
            raise RuntimeError(message)

    # determine sync environment
    if not os.environ.get('SYNC_ENV', None) and not config.get('config', 'SYNC_ENV', fallback=None):
        print("Please specify the environment with --env option or as SYNC_ENV in properties file. Using 'default'")
        config.set('config', 'SYNC_ENV', 'default')
    sync_env = config.get('config', 'SYNC_ENV', fallback=None)
    if not sync_env:
        sync_env = os.environ.get('SYNC_ENV', None)
    api_base_url = f"http://{config.get('server', 'API_HOST', fallback='')}" \
                   f":{config.get('server', 'API_PORT', fallback='5010')}/api"
    api_user = config.get(f"org_{organization}", 'API_USER', fallback='')
    api_pw = config.get(f"org_{organization}", 'API_PW', fallback='')
    ssh_user = config.get('ssh', 'SSH_USER', fallback=None)
    ssh_host = config.get('ssh', 'SSH_HOST', fallback=None)
    gitconfig.username = config.get('git', 'user_default', fallback=None)
    gitconfig.email = config.get('git', 'email_default', fallback=None)