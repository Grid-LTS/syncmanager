import argparse
import os, sys
from pathlib import Path

from .util.globalproperties import Globalproperties
from .util.syncconfig import SyncConfig
from .util.readconfig import ConfigParser, environment_parse

from .clients import ACTION_SET_REMOTE_ALIASES, ACTION_ADD_ENV_ALIASES, ACTION_PULL, ACTION_PUSH, ACTION_SET_CONF, \
    ACTION_SET_CONF_ALIASES, ACTION_DELETE, ACTION_ARCHIVE_IGNORED_FILES, ACTION_DELETE_REPO
from .clients.sync_client import SyncClient
from .clients.deletion_registration import DeletionRegistration
from .clients.sync_dir_registration import SyncDirRegistration
from .clients.sync_env_registration import SyncEnvRegistration
from .clients.git_archive_ignored import GitArchiveIgnoredFiles


def init_global_properties(_stage='dev', _org=''):
    if os.environ.get('SYNCMANAGER_STAGE'):
        stage = os.environ.get('SYNCMANAGER_STAGE')
    else:
        stage = _stage
    # initialize global properties
    Globalproperties.read_config(stage, _org)


def apply_sync_conf_files(root, filenames, action, force, sync_env, clients_enabled):
    for filename in filenames:
        path = os.path.join(root, filename)
        print(path)
        sync_envs = environment_parse(path)
        if len(sync_envs) > 0 and not sync_env in sync_envs:
            continue
        only_once = False
        config_parser = ConfigParser(path)
        for sync_config in config_parser.parse():
            if not sync_config.mode in clients_enabled:
                if not only_once:
                    only_once = True
                    print('Ignoring client ' + sync_config.mode + '.')
                continue
            only_once = False
            sync_client = SyncClient(action, sync_config, force)
            sync_client.sync_with_remote_repo(sync_config)


def register_local_branch_for_deletion(path, git_repo_path: Path):
    delete_action = DeletionRegistration(branch_path=path, git_repo_path=git_repo_path)
    delete_action.register_path()
    client = delete_action.mode
    if not client:
        print("Cannot determine sync client.", file=sys.stderr)
        exit(1)
    entries = delete_action.entries
    if not len(entries) > 0:
        exit(1)
    entry = entries[0]
    if delete_action.local_branch_exists:
        client_factory = SyncClient(ACTION_DELETE, entry.config, force=False)
        client_instance = client_factory.get_instance(entry.config)
        # delete the local branches
        client_instance.apply(path=path)
    else:
        print(f"Warning: you have not checked out this branch '{path}', but it will be completely wiped from "
              "all machines on the next sync.")


staging_envs = ['dev', 'tests', 'prod']
clients = ['git', 'unison']


def parse_arguments_legacy():
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
    return parser.parse_args()


def legacy():
    args = parse_arguments_legacy()
    init_global_properties(args.stage)
    if args.action in [ACTION_PULL, ACTION_PUSH]:
        action = args.action
    elif args.action in ACTION_SET_CONF_ALIASES:
        action = ACTION_SET_CONF
    elif args.action == ACTION_DELETE:
        path = args.path
        git_repo_path = Path(os.getcwd())
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
        sync_env = Globalproperties.sync_env

    if args.conf:
        if not os.path.dirname(args.conf):
            conf_file_root = Globalproperties.conf_dir
            conf_file_path = os.path.join(Globalproperties.conf_dir, args.conf)
        else:
            conf_file_root = os.path.dirname(args.conf)
            conf_file_path = args.conf
        if not os.path.exists(conf_file_path):
            print("File {} does not exist".format(args.conf))
            exit(1)
        apply_sync_conf_files(conf_file_root, [args.conf], action, force, sync_env, clients_enabled)
    else:
        # loop through all *.conf files in the directory
        for root, dirs, filenames in os.walk(Globalproperties.conf_dir):
            files = [fi for fi in filenames if fi.endswith(".conf")]
            apply_sync_conf_files(root, files, action, force, sync_env, clients_enabled)


def parse_arguments():
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
    parser.add_argument("-o", "--org", default="",
                        help="Specifies organization to be used.")
    parser.add_argument("-c", "--client", choices=clients, help="Restrict syncing to a certain client")
    parser.add_argument("-off", "--offline", action='store_true', help="when offline. server is not called")
    parser.add_argument("-dry", "--dryrun", action='store_true', help="dry run does not execution the action")
    parser.add_argument("-n", "--namespace", help="Restrict syncing to a certain namespace")
    parser.add_argument("-ry", "--retention_years",
                        help="Only sync repositories that have been updated at least inside the recent time frame given by retention years")
    allowed_actions = [ACTION_PUSH, ACTION_PULL, ACTION_ARCHIVE_IGNORED_FILES,
                       ACTION_DELETE_REPO] + ACTION_SET_REMOTE_ALIASES + ACTION_SET_CONF_ALIASES + ACTION_ADD_ENV_ALIASES
    sub_parser_action = parser.add_subparsers(dest='action', help="Action to perform")
    for act in allowed_actions:
        # Todo: improve see https://stackoverflow.com/questions/7498595/python-argparse-add-argument-to-multiple-subparsers
        sub_parser_std_action = sub_parser_action.add_parser(act)
    sub_parser_delete = sub_parser_action.add_parser(ACTION_DELETE)
    # add another positional argument to specify the path or branch to delete
    sub_parser_delete.add_argument('path', type=str)
    return parser.parse_args()


def main():
    args = parse_arguments()
    init_global_properties(args.stage, args.org)
    # determine the environment which is synced
    Globalproperties.init_allconfig(args)
    sync_config = SyncConfig.init(namespace=args.namespace, allconfig=Globalproperties.allconfig)
    if args.action == ACTION_DELETE:
        path = args.path
    else:
        path = None
    if args.retention_years:
        sync_config.retention_years = int(args.retention_years)
    execute_command(args, sync_config, path=path)


def execute_command(arguments, sync_config: SyncConfig, remote_name=None, path=None):
    single_repo_mode = sync_config.offline and Path(os.getcwd()).joinpath(".git").exists()
    if arguments.action in ACTION_SET_REMOTE_ALIASES + [ACTION_ARCHIVE_IGNORED_FILES, ACTION_DELETE,
                                                        ACTION_DELETE_REPO]:
        sync_config.local_path = Path(os.getcwd())
    if arguments.action in ACTION_SET_REMOTE_ALIASES:
        sync_config.remote_repo = remote_name
        new_sync_dir = SyncDirRegistration(sync_config=sync_config)
        new_sync_dir.register()
        return
    elif arguments.action in ACTION_ADD_ENV_ALIASES:
        new_sync_env = SyncEnvRegistration()
        new_sync_env.register()
        return
    elif arguments.action == ACTION_DELETE:
        register_local_branch_for_deletion(path, sync_config.local_path)
        return
    elif arguments.action in ACTION_SET_CONF_ALIASES:
        pass
    elif arguments.action in [ACTION_PULL, ACTION_PUSH]:
        pass
    elif arguments.action == ACTION_ARCHIVE_IGNORED_FILES:
        if single_repo_mode:
            processor = GitArchiveIgnoredFiles(sync_config)
            processor.apply()
            return
    elif arguments.action == ACTION_DELETE_REPO:
        sync_client = SyncClient(arguments.action, sync_config=sync_config, force=arguments.force)
        sync_client.sync_single_repo()
        return
    else:
        print('Unknown command \'{0}\'. Abort.'.format(arguments.action))
        exit(1)
    if arguments.client:
        clients_enabled = [arguments.client]
    else:
        clients_enabled = clients
    print('Enabled clients: ' + ', '.join(clients_enabled))
    for mode in clients_enabled:
        print(f"Syncing client {mode}")
        config = SyncConfig.from_sync_config(sync_config)
        config.mode = mode
        sync_client = SyncClient(arguments.action, config, arguments.force)
        sync_client.get_and_sync_repos()
