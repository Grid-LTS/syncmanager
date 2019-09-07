import re
from git import Repo

from ..util.system import sanitize_path


class GitClientSettings:

    def __init__(self):
        self.errors = []

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
        self.repo = Repo(self.source_path)
        conf_writer = self.repo.config_writer()
        print('Set git config for \'{0}\''.format(self.source_path_short))
        command_prefix = ['git', 'config']
        try:
            conf_writer.set_value('user', 'name', name)
        except Exception as err:
            print('Git config \'user.name\' could not be set. Error: ' + str(err))
        try:
            conf_writer.set_value('user', 'email', email)
        except Exception as err:
            print('Git config \'user.email\' could not be set. Error: ' + str(err))
        conf_writer.release()
        # check remote repository urls
        # if remote repo is not set, add it
        remote_repo = self.get_remote_repo()
        if remote_repo:
            # corresponds to 'git remote set-url <target_repo> <repo url>
            with remote_repo.config_writer as cw:
                cw.set("url", self.target_path)
                cw.release()
        else:
            # corresponds to 'git remote add <target_repo> <repo url>
            self.repo.create_remote(self.target_repo, self.target_path)

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

    def get_remote_repo(self):
        try:
            return self.repo.remote(self.target_repo)
        except ValueError:
            return False
