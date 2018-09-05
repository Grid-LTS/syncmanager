import argparse
import configparser
import os

from .util.readconfig import config_parse, environment_parse
from .clients import ACTION_PULL, ACTION_PUSH, ACTION_SET_CONF, ACTION_SET_CONF_ALIASES, ACTION_DELETE
from .clients.sync_client import SyncClientFactory, DeletionRegistration


def main():
    """
      Parses arguments and initiates the respective sync clients
    """
    clients = ['git', 'unison']
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", help="Specify file from which the sync config is loaded")
    parser.add_argument("-f", "--force", action='store_true', default=False,
                        help="Flag for forcing sync in case of conflicts, remote or local data is overwritten")
    parser.add_argument("--env",
                        help="Specify environment id, e.g. home, work. Default is written in the env variable $SYNC_ENV or in the properties file.")
    parser.add_argument("-c", "--client", choices=clients, help="Restrict syncing to a certain client")
    sub_parser_action = parser.add_subparsers(dest='action', help="Action to perform")
    for act in ['push', 'pull', 'set-conf', 'set-config']:
        sub_parser_std_action = sub_parser_action.add_parser(act)
    sub_parser_delete = sub_parser_action.add_parser('delete')
    # add another positional argument to specify the path or branch to delete
    sub_parser_delete.add_argument('path', type=str)
    args = parser.parse_args()
    if args.action in [ACTION_PULL, ACTION_PUSH]:
        action = args.action
    elif args.action in ACTION_SET_CONF_ALIASES:
        action = ACTION_SET_CONF
    elif args.action == ACTION_DELETE:
        path = args.path
        delete_action = DeletionRegistration(path)
        code = delete_action.register_path()
        exit(code)
    else:
        action = None
        print('Unknown command \'{0}\'. Abort.'.format(args.action))
        exit(1)
    force = args.force

    if __name__ == "__main__":
        properties_path = ""
    else:
        properties_path = "syncmanager"
    config = configparser.ConfigParser()
    if args.client:
        clients_enabled = [args.client]
    else:
        clients_enabled = clients
    print('Enabled clients: ' + ', '.join(clients_enabled))

    properties_path += "/server-sync.properties"
    if os.path.isfile(properties_path):
        config.read(properties_path)
    else:
        print("Please create server-sync.properties file in the project root.")
        exit(1)

    if not config['config'].get('conf_dir', None):
        print("Please specify the path to the config files in server-sync.properties.")
        exit(1)

    # determine the environment which is synced
    if args.env:
        sync_env = args.env
    else:
        if not os.environ.get('SYNC_ENV', None) and not config['config'].get('SYNC_ENV', None):
            print("Please specify the environment with --env option or as SYNC_ENV in properties file.")
            exit(1)
        sync_env = config['config'].get('SYNC_ENV', None)
        if not sync_env:
            sync_env = os.environ.get('SYNC_ENV', None)

    # loop through all *.conf files in the directory
    for root, dirs, filenames in os.walk(config['config'].get('conf_dir', None)):
        files = [fi for fi in filenames if fi.endswith(".conf")]
        for f in files:
            path = os.path.join(root, f)
            print(path)
            sync_envs = environment_parse(path)
            if len(sync_envs) > 0 and not sync_env in sync_envs:
                continue
            only_once = False
            for client, config in config_parse(path):
                if not client in clients_enabled:
                    if not only_once:
                        only_once = True
                        print('Ignoring client ' + client + '.')
                    continue
                only_once = False
                client_factory = SyncClientFactory(client, action)
                client_instance = client_factory.get_instance()
                if client_instance:
                    client_instance.set_config(config, force)
                    client_instance.apply()
