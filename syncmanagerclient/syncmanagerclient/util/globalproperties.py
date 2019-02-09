import os
import configparser

# this module encloses all globally accessible properties
properties_path_prefix = ''
conf_dir = ''
sync_env = ''
var_dir = ''


def set_prefix(prefix):
    global properties_path_prefix
    properties_path_prefix = prefix


def read_config():
    global properties_path_prefix
    global conf_dir
    global sync_env
    global var_dir
    properties_path = properties_path_prefix + "/server-sync.properties"
    config = configparser.ConfigParser()
    if os.path.isfile(properties_path):
        config.read(properties_path)
    else:
        print("Please create server-sync.properties file in the project root.")
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
        print("Please specify the environment with --env option or as SYNC_ENV in properties file.")
        exit(1)
    sync_env = config['config'].get('SYNC_ENV', None)
    if not sync_env:
        sync_env = os.environ.get('SYNC_ENV', None)
