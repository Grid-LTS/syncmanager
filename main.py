import argparse
import configparser


def main():
    """
      Parses arguments and initiates the respective sync clients
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=['push', 'pull', 'set-conf', 'set-config'], help="Action to perform")
    parser.add_argument("-f", "--file", help="Specify file from which the sync config is loaded")
    parser.add_argument("--env", help="Specify environment id, e.g. home, work. Default is written in the env variable DEV_ENV")
    args = parser.parse_args()

    if args.action in ['push', 'pull']:
        print('You will sync')
    elif args.action in ['set-conf', 'set-config']:
        print('Set config')
    if (__name__ == "__main__"):
        properties_path = ""
    else:
        properties_path = "sync-manager"
    config = configparser.ConfigParser()
    config.read(properties_path+"/server-sync.properties")