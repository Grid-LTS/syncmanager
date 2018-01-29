import argparse
import configparser
import os

from .util.readconfig import config_parse
from .clients import SyncClientFactory, ACTION_PULL, ACTION_PUSH, ACTION_SET_CONF, ACTION_SET_CONF_ALIASES


def main():
    """
      Parses arguments and initiates the respective sync clients
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=['push', 'pull', 'set-conf', 'set-config'], help="Action to perform")
    parser.add_argument("-c", "--conf", help="Specify file from which the sync config is loaded")
    parser.add_argument("-f", "--force", help="Flag for forcing sync in case of conflicts, remote or local data is overwritten")
    parser.add_argument("--env",
                        help="Specify environment id, e.g. home, work. Default is written in the env variable DEV_ENV")
    args = parser.parse_args()

    if args.action in [ACTION_PULL, ACTION_PUSH]:
        action = args.action
    elif args.action in ACTION_SET_CONF_ALIASES:
        action = ACTION_SET_CONF
    else:
        action = None
        print('Unknown command \'' + args.action + '\'. Abort.')
        exit(1)
    if args.force:
        force = True
    else:
        force = False

    if __name__ == "__main__":
        properties_path = ""
    else:
        properties_path = "syncmanager"
    config = configparser.ConfigParser()

    properties_path += "/server-sync.properties"
    if os.path.isfile(properties_path):
        config.read(properties_path)
    else:
        print ("Please create server-sync.properties file in the project root.")
        exit(1)

    if not config['config'].get('conf_dir', None):
        print ("Please specify the path to the config files in serve-sync.properties.")
        exit(1)

    # loop through all *.conf files in the directory
    for root, dirs, filenames in os.walk(config['config'].get('conf_dir', None)):
        files = [fi for fi in filenames if fi.endswith(".conf")]
        for f in files:
            path = os.path.join(root, f)
            for mode, config in config_parse(path):
                client_factory = SyncClientFactory(mode, action)
                client = client_factory.get_instance()
                if client:
                    client.set_config(config, force)
                    client.apply()