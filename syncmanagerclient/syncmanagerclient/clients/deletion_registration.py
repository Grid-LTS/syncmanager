import os
import re
from git import Repo
import syncmanagerclient.util.globalproperties as globalproperties


class DeletionRegistration:

    def __init__(self, **kwargs):
        self.branch_path = kwargs.get('branch_path', None)
        self.registry_dir = globalproperties.var_dir
        # first check if directory is a git working tree
        self.dir = kwargs.get('git_repo_path')
        self.configs = []
        self.mode = kwargs.get('mode', None)

    def get_mode(self):
        if os.path.isdir(self.dir + '/.git'):
            # first check if this branch exists
            self.gitrepo = Repo(self.dir)
            if not hasattr(self.gitrepo.heads, self.branch_path):
                print('There is no local branch ' + self.branch_path)
                self.mode = None
                return
            self.mode = 'git'
            return
        # to be implemented: Unison check

    def get_config(self):
        self.get_mode()
        if not self.mode:
            return None
        configs = []
        # get remote repo
        if self.mode == 'git':
            # fetch url of origin
            if self.gitrepo.remotes:
                for remote in self.gitrepo.remotes:
                    config = dict()
                    config['source'] = self.dir
                    config['url'] = iter(remote.urls)
                    config['remote_repo'] = remote.name
                    self.configs.append(config)
        elif self.mode == 'unison':
            # to be implemented
            pass

    def register_path(self):
        self.get_config()
        if self.mode == 'git':
            for config in self.configs:
                remote_repo_name = config.get('remote_repo', None)
                if not remote_repo_name:
                    continue
                registry_file = self.get_registry_file_path(remote_repo_name)
                f = open(registry_file, 'a+')
                entry = self.dir + '\t' + self.branch_path + '\n'
                f.write(entry)
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
