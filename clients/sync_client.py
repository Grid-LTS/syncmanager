import os
from git import Repo

from . import ACTION_PULL, ACTION_PUSH, ACTION_SET_CONF

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
            elif self.action in [ACTION_PUSH, ACTION_PULL]:
                return GitClientSync(self.action)
            else:
                raise Exception('Unknown command \'' + self.action + '\'.')
        else:
            print('unison')
            return None

class DeletionRegistration:

    def __init__(self, path):
        self.path = path
        clients_dir = os.path.dirname(os.path.realpath(__file__))
        self.registry_dir = os.path.dirname(clients_dir) + '/var'

    def get_mode(self):
        # first check if directory is a git working tree
        self.dir = os.getcwd()
        if os.path.isdir(self.dir + '/.git'):
            # first check if this branch exists
            gitrepo = Repo(self.dir)
            if not hasattr(gitrepo.heads, self.path):
                return None
            return 'git'
        #to be implemented: Unison check
        return None

    def register_path(self):
        mode = self.get_mode()
        if not mode:
            return None
        registry_file = self.registry_dir + '/' + mode + '.txt'
        if mode == 'git':
            f = open(registry_file,'+a')
            entry = self.dir + '\t' + self.path
            f.write(entry)
            f.close()

    def read_and_flush_registry(self, mode):
        registry_file = self.registry_dir + '/' + mode + '.txt'
        if mode == 'git':
            f = open(registry_file,'+a')
            entries = f.readlines()
            f.seek(0)
            f.truncate()
            f.close()
            return entries