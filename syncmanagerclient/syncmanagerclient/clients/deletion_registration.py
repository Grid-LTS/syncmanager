import os
import re

from typing import List

from git import Repo
import syncmanagerclient.util.globalproperties as globalproperties
from syncmanagerclient.util.syncconfig import SyncConfig
from .git_base import GitClientBase

class DeletionRegistrationEntry(GitClientBase):

    def __init__(self, config: SyncConfig, gitrepo=None):
        super().__init__(config, gitrepo)

    def get_remote_repo(self):
        return self.config.remote_repo



class DeletionRegistration():

    def __init__(self, **kwargs):
        super().__init__()
        self.branch_path = kwargs.get('branch_path', None)
        self.registry_dir = globalproperties.var_dir
        # first check if directory is a git working tree
        self.dir = kwargs.get('git_repo_path')
        self.entries : List[DeletionRegistrationEntry] = []
        self.mode = kwargs.get('mode', None)
        self.local_branch_exists = False
        self.gitrepo = None


    def get_mode(self):
        if os.path.isdir(os.path.join(self.dir, '.git')):
            # first check if this branch exists
            self.gitrepo = Repo(self.dir)
            if not hasattr(self.gitrepo.heads, self.branch_path):
                print('There is no local branch ' + self.branch_path)
                self.mode = 'git'
                return
            self.mode = 'git'
            self.local_branch_exists = True
            self.close()


    def get_config(self):
        self.get_mode()
        if not self.mode:
            return None
        # get remote repo
        if self.mode == 'git':
            # fetch url of origin
            if self.gitrepo.remotes:
                for remote in self.gitrepo.remotes:
                    remote_urls = []
                    for remote_url in remote.urls:
                        remote_urls.append(remote_url)
                    if len(remote_urls) > 1:
                        print(f"Multiple urls defined for this remote: {str(remote_urls)}. Skip")
                        continue
                    if len(remote_urls) == 0:
                        print(f"No remote url defined. Skip")
                        continue
                    remote_url = remote_urls[0]
                    config = SyncConfig()
                    config.local_path = self.dir
                    config.remote_repo_url = remote_url
                    config.remote_repo = remote.name
                    entry = DeletionRegistrationEntry(config, self.gitrepo)
                    self.entries.append(entry)
        elif self.mode == 'unison':
            # to be implemented
            pass

    def register_path(self):
        self.get_config()
        if self.mode == 'git':
            for entry in self.entries:
                remote_repo_name = entry.get_remote_repo()
                if not remote_repo_name:
                    continue
                registry_file = self.get_registry_file_path(remote_repo_name)
                f = open(registry_file, 'a+')
                registry_entry = self.dir + '\t' + self.branch_path + '\n'
                f.write(registry_entry)
                f.close()

    def get_registry_file_path(self, repo_name):
        return self.registry_dir + '/' + self.mode + '.' + repo_name + '.txt'

    def read_and_flush_registry(self, repo_name):
        registry_file = self.get_registry_file_path(repo_name)
        if not os.path.isfile(registry_file):
            return []
        f = open(registry_file, 'r+')
        entries = []
        lines = f.readlines()
        for line in lines:
            # replace spaces with tab, in case tab has been replaced by space in the meantime
            line = re.sub(' +', '\t', line)
            line = line.strip()
            if not line:
                continue
            entry = line.split('\t')
            entry[0] = entry[0].strip()
            entry[1] = entry[1].strip()
            entries.append(entry)
        f.seek(0)
        f.close()
        os.remove(registry_file)
        return entries

    def write_registry(self, repo_name, entries):
        registry_file = self.get_registry_file_path(repo_name)
        if len(entries) == 0:
            return
        f = open(registry_file, 'w+')
        for entry in entries:
            line = '\t'.join(entry) + '\n'
            f.write(line)
        f.close()


    def close(self):
        if self.gitrepo:
            self.gitrepo.close()
