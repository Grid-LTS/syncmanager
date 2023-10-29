import os
import configparser

# this module encloses all globally accessible properties
properties_path_prefix = ''
conf_dir = ''
sync_env = ''
var_dir = ''
api_base_url = ''
api_user = ''
api_pw = ''
ssh_user = ''
ssh_host = ''


def set_prefix(prefix):
    global properties_path_prefix
    properties_path_prefix = prefix


def read_config(stage, organization=''):
    global properties_path_prefix
    global conf_dir
    global sync_env
    global var_dir
    global api_base_url
    global api_user
    global api_pw
    global ssh_user
    global ssh_host
    if stage == 'prod':
        properties_file_name = "server-sync.properties"
    else:
        properties_file_name = f"server-sync.{stage}.properties"
    properties_path = os.path.join(properties_path_prefix, properties_file_name)
    config = configparser.ConfigParser()
    if not organization:
        organization = config['config'].get('org_default', 'default')
    if os.path.isfile(properties_path):
        config.read(properties_path)
    else:
        print(f"Please create {properties_file_name} file in the project root.")
        exit(1)
    conf_dir = config['config'].get('conf_dir', None)
    if not conf_dir:
        print("Please specify the path to the config files in server-sync.properties.")
        exit(1)
    var_dir = config['config'].get('var_dir', None)
    if not var_dir:
        print("Please specify the var_dir property in server-sync.properties.")
        exit(1)

    # determine sync environment
    if not os.environ.get('SYNC_ENV', None) and not config['config'].get('SYNC_ENV', None):
        print("Please specify the environment with --env option or as SYNC_ENV in properties file. Using 'default'")
        config['config'].set('SYNC_ENV', 'default')
    sync_env = config['config'].get('SYNC_ENV', None)
    if not sync_env:
        sync_env = os.environ.get('SYNC_ENV', None)
    api_base_url = f"http://{config['server'].get('API_HOST','')}:{config['server'].get('API_PORT','5010')}/api"
    api_user = config[f"org_{organization}"].get('API_USER', '')
    api_pw = config[f"org_{organization}"].get('API_PW', '')
    ssh_user = config['ssh'].get('SSH_USER', None)
    ssh_host = config['ssh'].get('SSH_HOST', None)
