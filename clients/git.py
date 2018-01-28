import re, os

from ..util.system import run, change_dir, sanitize_path

from . import ACTION_PULL, ACTION_PUSH, ACTION_SET_CONF


class GitClient:
    def __init__(self, action, config):
        self.action = action
        self.source_path_short = config.get('source', None)
        self.source_path = sanitize_path(self.source_path_short)
        self.target_repo = config.get('remote_repo', None)
        self.target_path = config.get('url', None)
        self.settings = config.get('settings', None)

    def apply(self):
        if (self.action == ACTION_PULL):
            self.sync_pull()
        elif (self.action == ACTION_PUSH):
            self.sync_push()
        elif (self.action == ACTION_SET_CONF):
            self.set_settings()
        else:
            raise Exception('Unknown command \'' + self.action + '\'.')

    def set_settings(self):
        """
        - sets the git config (name & email) that is specified the config files
        - also sets the remote repository url
        :return:
        """
        name, email = self.parse_settings()
        # change to the directory and apply git settings
        code = change_dir(self.source_path)
        if code == 1:
            print('Directory \'' + self.source_path_short + '\' is not accessible.')
            return None
        else:
            print('Set git config for \'' + self.source_path_short + '\'')
        command_prefix = ['git', 'config']
        set_name = command_prefix + ['user.name', name]
        output, errors = run(set_name, False)
        if (output != 0):
            print('Git config \'user.name\' could not be set. Reason: ' + errors)
        set_email = command_prefix + ['user.email', email]
        output, errors = run(set_email, False)
        if (output != 0):
            print('Git config \'user.email\' could not be set. Reason: ' + errors)
        # check remote repository urls
        # if remote repo is not set, add it
        if self.isset_remote_repo():
            set_remote = ['git', 'remote', 'set-url', self.target_repo, self.target_path]
        else:
            set_remote = ['git', 'remote', 'add', self.target_repo, self.target_path]
        output, errors = run(set_remote, False)
        if (output != 0):
            print('Remote repo url could not be set. Reason: ' + errors)

    def parse_settings(self):
        if not self.settings:
            return None
        settings = self.settings.strip()
        if settings[0] == '"':
            parts = re.split('"', settings[1:], maxsplit=1)
        else:
            parts = re.split(' ', settings, maxsplit=1)
        name = parts[0]
        email = parts[1].strip()
        return name, email

    def isset_remote_repo(self):
        command = ['git', 'remote']
        output, errors = run(command, True)
        repos = output.split('\n')
        return self.target_repo in repos

    def sync_pull(self):
        return None

    def sync_push(self):
        return None
