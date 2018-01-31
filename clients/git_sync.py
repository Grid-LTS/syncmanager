import re, os

from ..util.system import run, change_dir, sanitize_path

from . import ACTION_PULL, ACTION_PUSH


class GitClientSync:
    def __init__(self, action):
        self.action = action

    def set_config(self, config, force):
        self.local_path_short = config.get('source', None)
        self.local_path = sanitize_path(self.local_path_short)
        self.local_repo = os.path.basename(self.local_path)
        self.remote_repo = config.get('remote_repo', None)
        self.remote_path = config.get('url', None)
        self.settings = config.get('settings', None)
        self.force = force

    def apply(self):
        if (self.action == ACTION_PULL):
            self.sync_pull()
        elif (self.action == ACTION_PUSH):
            self.sync_push()

    def sync_pull(self):
        return None

    def sync_push(self):
        ret_code = self.change_to_local_repo()
        if ret_code == 0:
            self.git_fetch()
        branches = self.get_remote_branches()
        local_branch = branches[1]
        if len(branches) == 1:
            print('The local branch \'{0}\' has no upstream.'.format(local_branch))

    def get_remote_branches(self):
        cmd = ['git', 'for-each-ref', '--format=%(refname:short) %(push:short)', 'refs/heads/']
        output, errors = run(cmd, True)
        output = output.strip()
        if not output:
            return []
        branches = []
        lines = output.split('\n')
        for line in lines:
            branches += line.split(' ')
        return branches

    def git_fetch(self):
        git_fetch = ['git', 'fetch', self.remote_repo]
        ret_code, error = run(git_fetch, False)
        return ret_code

    def change_to_local_repo(self):
        # first check if the local repo exists and is a git working space
        repo_exists = os.path.isdir(self.local_path)
        local_path_base = os.path.basename(self.local_path)
        print('Change to Git project \'{0} \'.'.format(self.local_path_short))
        if os.path.isdir(self.local_path + '/.git'):
            ret_val = change_dir(self.local_path)
            if ret_val != 0:
                print('Cannot change to repository \'{0}\'.'.format(self.local_path))
            return ret_val
        elif repo_exists:
            print('The repository \'{0}\' exists, but is not a git repository'.format(self.local_path))
            return 1
        else:
            # local repo does not exist and must be cloned
            parent_dir = os.path.dirname(self.local_path)
            ret_code = 0
            if not os.path.isdir(parent_dir):
                make_dir = ['mkdir', '-p', parent_dir]
                ret_code, error = run(make_dir, False)
            if ret_code == 0:
                ret_code = change_dir(parent_dir)
            else:
                return ret_code
            if ret_code != 0:
                print('Could change to \'{0}\''.format(parent_dir))
                return ret_code
            # clone git repo
            git_clone = ['git', 'clone', '--origin', self.remote_repo, self.remote_path, local_path_base]
            print('Clone to remote repo \'{0}\' to \'{1}\'.'.format(self.remote_repo,self.local_path))
            ret_code, error = run(git_clone, False)
            if ret_code == 0:
                print('Success.')
                ret_code = change_dir(self.local_path)
            else:
                print('Remote repo could not be clone because of an error:' + error)
            return ret_code
