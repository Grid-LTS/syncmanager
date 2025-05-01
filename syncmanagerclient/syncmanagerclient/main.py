import argparse
import os, sys
from os.path import dirname
from pathlib import Path

import syncmanagerclient.util.globalproperties as globalproperties
from .util.syncconfig import SyncConfig
from .util.readconfig import ConfigParser, environment_parse

from .clients import ACTION_SET_REMOTE_ALIASES, ACTION_ADD_ENV_ALIASES, ACTION_PULL, ACTION_PUSH, ACTION_SET_CONF, \
    ACTION_SET_CONF_ALIASES, ACTION_DELETE
from .clients.sync_client import SyncClient
from .clients.deletion_registration import DeletionRegistration
from .clients.sync_dir_registration import SyncDirRegistration
from .clients.sync_env_registration import SyncEnvRegistration


def init_global_properties(_stage='dev', _org=''):
    if os.environ.get('SYNCMANAGER_STAGE'):
        stage = os.environ.get('SYNCMANAGER_STAGE')
    else:
        stage = _stage
    # initialize global properties
    properties_path_prefix = dirname(dirname(os.path.abspath(__file__)))
    globalproperties.set_prefix(properties_path_prefix)
    globalproperties.read_config(stage, _org)


def apply_sync_conf_files(root, filenames, action, force, sync_env, clients_enabled):
    for filename in filenames:
        path = os.path.join(root, filename)
        print(path)
        sync_envs = environment_parse(path)
        if len(sync_envs) > 0 and not sync_env in sync_envs:
            continue
        only_once = False
        config_parser = ConfigParser(path)
        for client, config in config_parser.parse():
            if not client in clients_enabled:
                if not only_once:
                    only_once = True
                    print('Ignoring client ' + client + '.')
                continue
            only_once = False
            sync_client = SyncClient(client, action, sync_env, force)
            sync_client.sync_with_remote_repo(config)


def register_local_branch_for_deletion(path, git_repo_path):
    delete_action = DeletionRegistration(branch_path=path, git_repo_path=git_repo_path)
    delete_action.register_path()
    client = delete_action.mode
    if not client:
        print("Cannot determine sync client.", file=sys.stderr)
        exit(1)
    configs = delete_action.configs
    if not len(configs) > 0:
        exit(1)
    config = configs[0]
    if delete_action.local_branch_exists:
        client_factory = SyncClient(client, ACTION_DELETE, force=False)
        client_instance = client_factory.get_instance(config)
        # delete the local branches
        client_instance.apply(path=path)
    else:
        print("Warning: you have not checked out this branch, but it will be completely wiped from "
              "all machines on the next sync.")


staging_envs = ['dev', 'tests', 'prod']
clients = ['git','unison']


def legacy():
    global clients
    global staging_envs
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", help="Specify file from which the sync config is loaded")
    parser.add_argument("-f", "--force", action='store_true', default=False,
                        help="Flag for forcing sync in case of conflicts, remote or local data is overwritten")
    parser.add_argument("--env",
                        help="Specify environment id, e.g. home, work. Default is written in the env variable $SYNC_ENV or in the properties file.")
    parser.add_argument("--stage", choices=staging_envs, default="prod",
                        help="Specify staging environment to be used.")
    parser.add_argument("-c", "--client", choices=clients, help="Restrict syncing to a certain client")
    sub_parser_action = parser.add_subparsers(dest='action', help="Action to perform")
    for act in ['push', 'pull', 'set-conf', 'set-config']:
        sub_parser_std_action = sub_parser_action.add_parser(act)
    sub_parser_delete = sub_parser_action.add_parser('delete')
    # add another positional argument to specify the path or branch to delete
    sub_parser_delete.add_argument('path', type=str)
    args = parser.parse_args()
    init_global_properties(args.stage)
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

    
    if args.conf:
        if not os.path.dirname(args.conf):
            conf_file_root = globalproperties.conf_dir
            conf_file_path = os.path.join(globalproperties.conf_dir, args.conf)
        else:
            conf_file_root = os.path.dirname(args.conf)
            conf_file_path = args.conf
        if not os.path.exists(conf_file_path):
            print("File {} does not exist".format(args.conf))
            exit(1)
        apply_sync_conf_files(conf_file_root, [args.conf], action, force, sync_env, clients_enabled)
    else:
        # loop through all *.conf files in the directory
        for root, dirs, filenames in os.walk(globalproperties.conf_dir):
            files = [fi for fi in filenames if fi.endswith(".conf")]
            apply_sync_conf_files(root, files, action, force, sync_env, clients_enabled)


def main():
    """
      Parses arguments and initiates the respective sync clients
    """
    global clients
    global staging_envs
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--force", action='store_true', default=False,
                        help="Flag for forcing sync in case of conflicts, remote or local data is overwritten")
    parser.add_argument("--env",
                        help="Specify environment id, e.g. home, work. Default is written in the env variable " +
                             "$SYNC_ENV or in the properties file.")
    parser.add_argument("--stage", choices=staging_envs, default="prod",
                        help="Specify staging environment to be used.")
    parser.add_argument("-o","--org", default="",
                        help="Specifies organization to be used.")
    parser.add_argument("-c", "--client", choices=clients, help="Restrict syncing to a certain client")
    parser.add_argument("-n", "--namespace", help="Restrict syncing to a certain namespace")
    sub_parser_action = parser.add_subparsers(dest='action', help="Action to perform")
    for act in ['push', 'pull', 'add-env', 'set-remote', 'set-conf', 'set-config']:
        # Todo: improve see https://stackoverflow.com/questions/7498595/python-argparse-add-argument-to-multiple-subparsers
        sub_parser_std_action = sub_parser_action.add_parser(act)
    sub_parser_delete = sub_parser_action.add_parser('delete')
    # add another positional argument to specify the path or branch to delete
    sub_parser_delete.add_argument('path', type=str)
    args = parser.parse_args()
    init_global_properties(args.stage, args.org)
    # determine the environment which is synced
    if args.env:
        sync_env = args.env
    else:
        sync_env = globalproperties.sync_env
    if args.action == ACTION_DELETE:
        path = args.path
    else:
        path = None
    execute_command(args.action, args.client, sync_env, args.namespace, path, args.force)


def execute_command(action, client, sync_env, namespace, remote_name=None, path=None, force=False):
    if action in ACTION_SET_REMOTE_ALIASES:
        local_path = Path(os.getcwd())
        gitconfig = SyncConfig.init(remote_repo=remote_name, allconfig = globalproperties.allconfig)
        new_sync_dir = SyncDirRegistration(local_path=local_path, sync_env=sync_env, namespace=namespace, sync_config=gitconfig)
        new_sync_dir.register()
        return
    elif action in ACTION_ADD_ENV_ALIASES:
        new_sync_env = SyncEnvRegistration()
        new_sync_env.register()
        return
    elif action == ACTION_DELETE:
        git_repo_path = os.getcwd()
        register_local_branch_for_deletion(path, git_repo_path)
        return
    elif action in ACTION_SET_CONF_ALIASES:
        return
    elif action in [ACTION_PULL, ACTION_PUSH]:
        pass
    else:
        print('Unknown command \'{0}\'. Abort.'.format(action))
        exit(1)
    if client:
        clients_enabled = [client]
    else:
        clients_enabled = clients
    print('Enabled clients: ' + ', '.join(clients_enabled))
    for mode in clients_enabled:
        print(f"Syncing client {mode}")
        sync_client = SyncClient(mode, action, sync_env, force, namespace)
        sync_client.get_and_sync_repos()
