import os
from git import Repo

from . import ACTION_PULL, ACTION_PUSH, ACTION_DELETE, ACTION_SET_CONF

from .git_settings import GitClientSettings
from .git_sync import GitClientSync


class SyncClientFactory:
    def __init__(self, mode, action):
        self.mode = mode
        self.action = action

    def get_instance(self):
        if self.mode == 'git':
            if self.action == ACTION_SET_CONF:
                return GitClientSettings()
            elif self.action in [ACTION_PUSH, ACTION_PULL, ACTION_DELETE]:
                return GitClientSync(self.action)
            else:
                raise Exception('Unknown command \'' + self.action + '\'.')
        else:
            # to be implemented
            print('unison')
            return None


class DeletionRegistration:

    def __init__(self, path):
        self.path = path
        clients_dir = os.path.dirname(os.path.realpath(__file__))
        self.registry_dir = os.path.dirname(clients_dir) + '/var'
        # first check if directory is a git working tree
        self.dir = os.getcwd()
        self.configs = []
        self.mode = None

    def get_mode(self):
        if os.path.isdir(self.dir + '/.git'):
            # first check if this branch exists
            self.gitrepo = Repo(self.dir)
            if not hasattr(self.gitrepo.heads, self.path):
                print('There is no local branch ' + self.path)
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
                registry_file = self.registry_dir + '/' + self.mode + '.' + remote_repo_name + '.txt'
                f = open(registry_file, '+a')
                entry = self.dir + '\t' + self.path
                f.write(entry)
                f.close()

    def read_and_flush_registry(self, mode):
        registry_file = self.registry_dir + '/' + mode + '.txt'
        if mode == 'git':
            f = open(registry_file, '+a')
            entries = f.readlines()
            f.seek(0)
            f.truncate()
            f.close()
            return entries
