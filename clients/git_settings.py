import re

from ..util.system import run, change_dir, sanitize_path


class GitClientSettings:
    def set_config(self, config, *args):
        self.source_path_short = config.get('source', None)
        self.source_path = sanitize_path(self.source_path_short)
        self.target_repo = config.get('remote_repo', None)
        self.target_path = config.get('url', None)
        self.settings = config.get('settings', None)

    def apply(self):
        self.set_settings()

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
            print('Directory \'{0}\' is not accessible.'.format(self.source_path_short))
            return None
        else:
            print('Set git config for \'{0}\''.format(self.source_path_short))
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
