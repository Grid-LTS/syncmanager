import os
import os.path as osp

import pathlib
from git import Repo

from .api import ApiService
import syncmanagerclient.util.globalproperties as globalproperties


class SyncDirRegistration:
    mode = None

    def __init__(self, local_path, sync_env):
        home_dir = osp.expanduser('~')
        self.local_path = local_path
        if osp.commonprefix([local_path, home_dir]) == home_dir:
            self.local_path_short = '~/' + osp.relpath(local_path, home_dir)
        else:
            self.local_path_short = local_path
        self.gitrepo = None
        self.sync_env = sync_env
        self.mode = self.get_mode()
        self.api_service = ApiService(self.mode, self.sync_env)
        self.existing_repos_env_ids = []
        self.server_repo_ref = None
        self.other_envs_repos = None

    def get_mode(self):
        if os.path.isdir(self.local_path + '/.git'):
            # first check if this branch exists
            self.gitrepo = Repo(self.local_path)
            return 'git'
        else:
            print('Cannot determine the synchronization protocol')
            exit(1)
        # Todo implement Unison check

    def register(self):
        existing_repos_all = self.api_service.list_repos_all_client_envs(full=True)
        if not self.sync_env in existing_repos_all:
            print(f"You have no environment with name '{self.sync_env}' configured.")
            exit(1)
        existing_repos_env = existing_repos_all[self.sync_env]
        del existing_repos_all[self.sync_env]
        self.other_envs_repos = existing_repos_all
        print(f"{self.sync_env}:")
        is_update = False
        for repo_ref in existing_repos_env:
            p = pathlib.Path(repo_ref['git_repo']['server_path_rel'])
            print(f"{p.relative_to(*p.parts[:1])}")
            self.existing_repos_env_ids.append(repo_ref['git_repo']['id'])
            if not repo_ref['remote_name'] in self.gitrepo.remotes:
                continue
            url = next(self.gitrepo.remote(repo_ref['remote_name']).urls)
            if url == SyncDirRegistration.get_remote_url(repo_ref['git_repo']['server_path_absolute']):
                self.server_repo_ref = repo_ref
                is_update = True
        if is_update:
            self.update_reference()
        else:
            self.create_reference()

    def create_reference(self):
        other_env_repos = dict()
        other_env_repos_ids = []
        server_path_rels_of_other_repo = []
        for other_env in self.other_envs_repos:
            other_env_repos[other_env] = []
            print()
            print(f"{other_env}:")
            for other_repo in self.other_envs_repos[other_env]:
                other_repo_id = other_repo['git_repo']['id']
                if not other_repo_id in self.existing_repos_env_ids and not other_repo_id in other_env_repos_ids:
                    other_env_repos[other_env].append(other_repo)
                    other_env_repos_ids.append(other_repo_id)
                    p = pathlib.Path(other_repo['git_repo']['server_path_rel'])
                    server_path_rel_of_other_repo = p.relative_to(*p.parts[:1])
                    server_path_rels_of_other_repo.append(str(server_path_rel_of_other_repo))
                    print(f"{server_path_rel_of_other_repo}")

        print()
        server_path_rel = input('Enter namespace of your repo. e.g. my/path (or skip): ').strip()
        remote_name = ''
        is_overwrite = False
        while not remote_name:
            remote_name = input('Name of remote repo (default: origin): ').strip()
            if not remote_name:
                remote_name = 'origin'
            try:
                self.gitrepo.remote(remote_name)
                print(f"Remote repository with identifier {remote_name} already exists.")
                confirm = input(
                    f"Overwrite url of remote '{remote_name}'?. 'Y/y/yes' or other input for 'no': ").strip()
                if confirm in ['Y', 'y', 'yes']:
                    is_overwrite = True
                    break

                else:
                    remote_name = ''
                print("")
            except ValueError:
                pass
        repo_name = input('Enter directory name of bare repository (optional): ').strip()
        if not repo_name:
            repo_name = osp.basename(self.local_path_short)
        if repo_name[-4:] != '.git':
            repo_name += '.git'
        server_path = osp.join(server_path_rel, repo_name)
        all_sync_env = False
        # in case the desired remote repo is already created and registered for other environments, we only
        # register this env as client
        if not server_path in server_path_rels_of_other_repo:
            all_envs = input("Should all environments sync this repo? 'Y/y/yes' or other input for 'no': ").strip()
            if all_envs in ['Y', 'y', 'yes']:
                all_sync_env = True
        else:
            print(
                f"Your repo at {self.local_path_short} is registered as a downstream repo of the existing remote under namespace " +
                f"{server_path} for the environment {self.sync_env}.")
        response = self.api_service.create_remote_repository(self.local_path_short, server_path_rel,
                                                             repo_name, remote_name, all_sync_env)
        if response['is_new_reference']:
            remote_url = SyncDirRegistration.get_remote_url(response['server_path_absolute'])
            if is_overwrite:
                remote = self.gitrepo.remote(remote_name)
                remote.set_url(remote_url)
                print(f"Set URL at path {response['server_path_absolute']} for remote {remote_name}.")
            else:
                self.gitrepo.create_remote(remote_name, remote_url)
                print(f"Bare repo at path {response['server_path_absolute']} is registered as remote {remote_name}.")
        else:
            print(f"Bare repo at path {response['server_path_absolute']} is already registered as remote.")

    def update_reference(self):
        git_repo, gitrepo_reference = self.api_service.update_server_repo_reference(
            self.server_repo_ref['git_repo']['id'],
            self.local_path_short)
        # check if path changed
        if self.server_repo_ref['local_path_rel'] != gitrepo_reference['local_path_rel']:
            print(f"Updated local path to {gitrepo_reference['local_path_rel']}")
        else:
            print(f"The registered local path {gitrepo_reference['local_path_rel']} did not change.")

    @staticmethod
    def get_remote_url(remote_repo_path):
        return f"ssh://{globalproperties.ssh_user}@{globalproperties.ssh_host}:{remote_repo_path}"
