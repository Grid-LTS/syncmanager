import argparse
import os
from os.path import dirname
import syncmanagerclient.util.globalproperties as globalproperties

from .util.readconfig import config_parse, environment_parse

from .clients import ACTION_PULL, ACTION_PUSH, ACTION_SET_CONF, ACTION_SET_CONF_ALIASES, ACTION_DELETE
from .clients.sync_client import SyncClientFactory
from .clients.deletion_registration import DeletionRegistration


def apply_sync_conf_files(root, filenames, action, force, sync_env, clients_enabled):
    for filename in filenames:
        path = os.path.join(root, filename)
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


def register_local_branch_for_deletion(path, git_repo_path):
    delete_action = DeletionRegistration(path=path, git_repo_path=git_repo_path)
    delete_action.register_path()
    client = delete_action.mode
    configs = delete_action.configs
    if not len(configs) > 0:
        exit(1)
    config = configs[0]
    client_factory = SyncClientFactory(client, ACTION_DELETE)
    client_instance = client_factory.get_instance()
    client_instance.set_config(config, False)
    # delete the local branches
    client_instance.apply(path=path)


def main():
    # initialize global properties

    properties_path_prefix = dirname(__file__)
    globalproperties.set_prefix(properties_path_prefix)
    globalproperties.read_config()

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
        git_repo_path = os.getcwd()
        register_local_branch_for_deletion(path, git_repo_path)
        exit(0)
    else:
        action = None
        print('Unknown command \'{0}\'. Abort.'.format(args.action))
        exit(1)
    force = args.force

    if args.client:
        clients_enabled = [args.client]
    else:
        clients_enabled = clients
    print('Enabled clients: ' + ', '.join(clients_enabled))

    # determine the environment which is synced
    if args.env:
        sync_env = args.env
    else:
        sync_env = globalproperties.sync_env

    # loop through all *.conf files in the directory
    for root, dirs, filenames in os.walk(globalproperties.conf_dir):
        files = [fi for fi in filenames if fi.endswith(".conf")]
        apply_sync_conf_files(root, files, action, force, sync_env, clients_enabled)
