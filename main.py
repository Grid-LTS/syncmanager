import argparse
import configparser
import os
from pathlib import Path

from .util.readconfig import config_parse


def main():
    """
      Parses arguments and initiates the respective sync clients
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=['push', 'pull', 'set-conf', 'set-config'], help="Action to perform")
    parser.add_argument("-f", "--file", help="Specify file from which the sync config is loaded")
    parser.add_argument("--env",
                        help="Specify environment id, e.g. home, work. Default is written in the env variable DEV_ENV")
    args = parser.parse_args()

    if args.action in ['push', 'pull']:
        action = args.action
    elif args.action in ['set-conf', 'set-config']:
        action = 'set-conf'
    if __name__ == "__main__":
        properties_path = ""
    else:
        properties_path = "sync-manager"
    config = configparser.ConfigParser()

    properties_path += "/server-sync.properties"
    properties_file = Path(properties_path)
    if properties_file.is_file():
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
            for config in config_parse(path):
                print(config)
