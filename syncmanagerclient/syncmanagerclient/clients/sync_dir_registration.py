import os.path as osp

import pathlib

from ..util.syncconfig import SyncConfig

from git import Repo

from .api import ApiService
from .git_settings import GitClientSettings
import syncmanagerclient.util.globalproperties as globalproperties



class SyncDirRegistration:
    mode = None

    def __init__(self, sync_env, namespace=None, sync_config : SyncConfig=None):
        self.local_path = sync_config.local_path
        self.local_path_short = sync_config.local_path_short
        self.gitrepo = None
        self.sync_env = sync_env
        self.mode = self.get_mode()
        self.api_service = ApiService(self.mode, self.sync_env)
        self.existing_repos_env_ids = []
        self.server_repo_ref = None
        self.other_envs_repos = None
        self.server_path_rels_of_other_repo = []
        self.sync_config = sync_config
        self.remote_name = sync_config.remote_repo
        self.namespace = namespace


    def get_mode(self):
        if self.local_path.joinpath('.git').resolve().is_dir():
            # first check if this branch exists
            self.gitrepo = Repo(self.local_path)
            return 'git'
        else:
            print('Cannot determine the synchronization protocol')
            exit(1)
        # Todo implement Unison check

    def find_server_repo_for_env(self, sync_env, existing_repos_all):
        if not sync_env in existing_repos_all:
            print(f"You have no environment with name '{sync_env}' configured.")
            exit(1)
        existing_repos_env = existing_repos_all[sync_env]
        for repo_ref in existing_repos_env:
            self.existing_repos_env_ids.append(repo_ref['git_repo']['id'])
            # remote repo references from Git
            remote_objs = [x for x in self.gitrepo.remotes if x.name == repo_ref['remote_name']]
            if len(remote_objs) == 0:
                continue
            url = next(self.gitrepo.remote(repo_ref['remote_name']).urls)
            # find entry for repo in the list from the server by comparing the url of the remotes with the
            # one provided by Git
            if url == SyncDirRegistration.get_remote_url(repo_ref['git_repo']['server_path_absolute']):
                return repo_ref

    def register(self):
        existing_repos_all = self.api_service.list_repos_all_client_envs(full=True)
        if not existing_repos_all:
            existing_repos_env = []
        else:
            existing_repos_env = existing_repos_all[self.sync_env]
        print(f"{self.sync_env}:")
        for repo_ref in existing_repos_env:
            print(f"{self.remove_first_path_part(repo_ref['git_repo']['server_path_rel'])}")
            self.existing_repos_env_ids.append(repo_ref['git_repo']['id'])
        self.server_repo_ref = self.find_server_repo_for_env(self.sync_env, existing_repos_all)
        del existing_repos_all[self.sync_env]
        self.other_envs_repos = existing_repos_all
        is_update = self.server_repo_ref is not None
        # check if the repo might be registered under the default env
        server_repo_ref_default = self.find_server_repo_for_env('default', existing_repos_all)
        server_path_rel = self.namespace
        if server_repo_ref_default:
            namespace_parts = pathlib.Path(server_repo_ref_default['git_repo']['server_path_rel']).parts[1:-1]
            if len(namespace_parts) == 1:
                server_path_rel = namespace_parts[0]
            elif len(namespace_parts) > 1:
                server_path_rel = osp.join(namespace_parts[0], *namespace_parts[1:])
        self.print_other_env_repos()
        if is_update:
            self.update_reference()
        else:
            self.create_reference(server_path_rel)
        # update the git config
        gitsettings = GitClientSettings(self.sync_config, self.gitrepo)
        gitsettings.set_user_config()

    def print_other_env_repos(self):
        other_env_repos = dict()
        other_env_repos_ids = []
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
                    self.server_path_rels_of_other_repo.append(str(server_path_rel_of_other_repo))
                    print(f"{server_path_rel_of_other_repo}")
        print()

    def remove_first_path_part(self, path):
        p = pathlib.Path(path)
        return p.relative_to(*p.parts[:1])

    def first_path_part(self, path):
        p = pathlib.Path(path)
        return p.parts[0]

    def last_path_part(self, path):
        p = pathlib.Path(path)
        return p.parts[-1]

    def user_owns_repo(self, server_repo_ref):
        return server_repo_ref['user'] == self.first_path_part(server_repo_ref['git_repo']['server_path_rel'])

    def prompt_for_repo_name(self):
        if not globalproperties.test_mode:
            repo_name = input('Enter directory name of bare repository (optional): ').strip()
        else:
            repo_name = ''
        if not repo_name:
            repo_name = osp.basename(self.local_path_short)
        if repo_name[-4:] != '.git':
            repo_name += '.git'
        return repo_name

    def create_reference(self, _server_path_rel=''):
        if not _server_path_rel:
            server_path_rel = input('Enter namespace of your repo. e.g. my/path (or skip): ').strip()
        else:
            server_path_rel = _server_path_rel
        is_overwrite = False
        while not self.remote_name:
            self.remote_name = input('Name of remote repo (default: origin): ').strip()
            if not self.remote_name:
                self.remote_name = 'origin'
            try:
                self.gitrepo.remote(self.remote_name)
                print(f"Remote repository with identifier {self.remote_name} already exists.")
                confirm = input(
                    f"Overwrite url of remote '{self.remote_name}'?. 'Y/y/yes' or other input for 'no': ").strip()
                if confirm in ['Y', 'y', 'yes']:
                    is_overwrite = True
                    break

                else:
                    self.remote_name = ''
                print("")
            except ValueError:
                pass
        repo_name = self.prompt_for_repo_name()
        server_path = osp.join(server_path_rel, repo_name)
        all_sync_env = False
        # in case the desired remote repo is already created and registered for other environments, we only
        # register this env as client
        if not server_path in self.server_path_rels_of_other_repo and not globalproperties.test_mode:
            all_envs = input("Should all environments sync this repo? 'Y/y/yes' or other input for 'no': ").strip()
            if all_envs in ['Y', 'y', 'yes']:
                all_sync_env = True
        else:
            print(
                f"Your repo at {self.local_path_short} is registered as a downstream repo of the existing remote under namespace " +
                f"{server_path} for the environment {self.sync_env}.")
        response = self.api_service.create_remote_repository(self.local_path_short, server_path_rel,
                                                             repo_name, self.remote_name, all_sync_env)
        if response['is_new_reference']:
            remote_url = SyncDirRegistration.get_remote_url(response['server_path_absolute'])
            if is_overwrite:
                remote = self.gitrepo.remote(self.remote_name)
                remote.set_url(remote_url)
                print(f"Set URL at path {response['server_path_absolute']} for remote {self.remote_name}.")
            else:
                self.gitrepo.create_remote(self.remote_name, remote_url)
                print(f"Bare repo at path {response['server_path_absolute']} is registered as remote {self.remote_name}.")
        else:
            print(f"Bare repo at path {response['server_path_absolute']} is already registered as remote.")

    def update_reference(self):
        is_update_namespace = 'n'
        if self.user_owns_repo(self.server_repo_ref):
            is_update_namespace = input(
                "Do you want to change the namespace of the repo? 'Y/y/yes' or other input for 'no': ").strip()
        if is_update_namespace in ['Y', 'y', 'yes']:
            server_path_rel = input('Enter namespace of your repo. e.g. my/path (or skip): ').strip()
            repo_name = self.prompt_for_repo_name()
            server_path_rel = f"{self.server_repo_ref['user']}/{server_path_rel}/{repo_name}"
        else:
            server_path_rel = self.server_repo_ref['git_repo']['server_path_rel']
        git_repo, gitrepo_reference = self.api_service.update_server_repo_reference(
            self.server_repo_ref['git_repo']['id'],
            self.local_path_short, server_path_rel)
        # check if path changed
        if self.server_repo_ref['local_path_rel'] != gitrepo_reference['local_path_rel']:
            print(f"Updated local path to {gitrepo_reference['local_path_rel']}")
        else:
            print(f"The registered local path {gitrepo_reference['local_path_rel']} did not change.")
        remote_url = SyncDirRegistration.get_remote_url(git_repo['server_path_absolute'])
        remote_name = gitrepo_reference['remote_name']
        remote = self.gitrepo.remote(remote_name)
        remote.set_url(remote_url)
        self.sync_config.remote_repo = remote_name
        self.sync_config.remote_repo_url = remote_url
        print(f"Set URL at path {git_repo['server_path_absolute']} for remote {remote_name}.")

    @staticmethod
    def get_remote_url(remote_repo_path):
        if globalproperties.ssh_user and globalproperties.ssh_host:
            return f"ssh://{globalproperties.ssh_user}@{globalproperties.ssh_host}:{remote_repo_path}"
        return f"file:///{remote_repo_path}"
