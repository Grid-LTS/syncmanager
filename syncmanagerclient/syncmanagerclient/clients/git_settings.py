from git import Repo, InvalidGitRepositoryError

from ..util.syncconfig import SyncConfig
from .git_base import GitClientBase
from .error import GitErrorItem

class GitClientSettings(GitClientBase):

    def __init__(self, config : SyncConfig, gitrepo = None):
        super().__init__(config, gitrepo)

    def apply(self):
        self.set_settings()

    def set_settings(self):
        """
        - sets the git config (name & email) that is specified the config files
        - also sets the remote repository url
        :return:
        """
        self.initialize()
        print('Set git config for \'{0}\''.format(self.local_path_short))
        command_prefix = ['git', 'config']
        self.set_user_config()
        # check remote repository urls
        # if remote repo is not set, add it
        remote_repo = self.get_remote_repo()
        if remote_repo:
            # corresponds to 'git remote set-url <target_repo> <repo url>
            with remote_repo.config_writer as cw:
                cw.set("url", self.config.remote_repo_url)
                cw.release()
        else:
            # corresponds to 'git remote add <target_repo> <repo url>
            self.gitrepo.create_remote(self.config.remote_repo, self.config.remote_repo_url)
        self.close()

    def set_user_config(self):
        self.initialize()
        conf_writer = self.gitrepo.config_writer()
        if self.config.username:
            try:
                conf_writer.set_value('user', 'name', self.config.username)
            except Exception as err:
                print('Git config \'user.name\' could not be set. Error: ' + str(err))
        if self.config.email:
            try:
                conf_writer.set_value('user', 'email', self.config.email)
            except Exception as err:
                print('Git config \'user.email\' could not be set. Error: ' + str(err))
        conf_writer.release()

    def initialize(self):
        if not self.gitrepo:
            # change to the directory and apply git settings
            try:
                self.gitrepo = Repo(self.local_path)
            except InvalidGitRepositoryError as err:
                self.errors.append(
                    GitErrorItem(self.local_path_short, err, "Invalid local repo")
                )
                return

    def get_remote_repo(self):
        try:
            return self.gitrepo.remote(self.config.remote_repo)
        except ValueError:
            return False
