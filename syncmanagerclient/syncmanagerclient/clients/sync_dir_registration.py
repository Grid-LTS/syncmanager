import os
import os.path as osp

import pathlib
from git import Repo

from .api import ApiService
import syncmanagerclient.util.globalproperties as globalproperties


class SyncDirRegistration:
    mode = None

    def __init__(self, local_path):
        home_dir = osp.expanduser('~')
        self.local_path = local_path
        if osp.commonprefix([local_path, home_dir]) == home_dir:
            self.local_path_short = '~/' + osp.relpath(local_path, home_dir)
        else:
            self.local_path_short = local_path
        self.gitrepo = None
        self.mode = self.get_mode()

    def get_mode(self):
        if os.path.isdir(self.local_path + '/.git'):
            # first check if this branch exists
            self.gitrepo = Repo(self.local_path)
            return 'git'
        else:
            print('Cannot determine the synchronization protocol')
            exit(1)
        # to be implemented: Unison check

    def register(self, sync_env):
        api_service = ApiService(self.mode, sync_env)
        existing_repos = api_service.list_repos_by_client_env(full=True)
        for repo in existing_repos:
            p = pathlib.Path(repo['git_repo']['server_path_rel'])
            print(f"{p.relative_to(*p.parts[:1])}")
        server_path_rel = input('Enter namespace of your repo. e.g. my/path (or skip): ')
        remote_name = ''
        while not remote_name:
            remote_name = input('Name of remote repo (default: origin): ')
            if not remote_name:
                remote_name = 'origin'
            try:
                self.gitrepo.remote(remote_name)
                print(f"Remote repository with identifier {remote_name} already exists.")
                remote_name = ''
                print("\n")
            except ValueError:
                pass
        repo_name = input('Enter name of bare repository (optional): ')
        all_envs = input("Should all environments sync this repo? 'Y/y/yes' or 'No' for other input ")
        if all_envs in ['Y', 'y', 'yes']:
            all_sync_env = True
        else:
            all_sync_env = False
        response = api_service.create_remote_repository(self.local_path_short, server_path_rel,
                                                        repo_name, remote_name, all_sync_env)
        if response['is_new_reference']:
            remote_url = f"ssh://{globalproperties.ssh_user}@{globalproperties.ssh_host}:{response['remote_repo_path']}"
            self.gitrepo.create_remote(remote_name, remote_url)
            print(f"Bare repo at path {response['remote_repo_path']} is registered as remote {repo_name}.")
        else:
            print(f"Bare repo at path {response['remote_repo_path']} is already registered as remote.")
