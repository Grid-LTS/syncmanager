import os
import stat
import sys
import subprocess

from pathlib import Path

from ..util.error import InvalidArgument
from ..util.system import run_command
from ..util.globalproperties import Globalproperties

from ..util.syncconfig import SyncConfig
from .git_base import GitClientBase
from .error import GitErrorItem

class GitClientSettings(GitClientBase):

    def __init__(self, config : SyncConfig, gitrepo = None):
        super().__init__(config, gitrepo)

    def apply(self):
        self.set_settings()
        self.reinitialize_repo()

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

    def reinitialize_repo(self):
        if not self.local_path.joinpath(".git").resolve().exists():
            err_msg = f"{self.local_path} is not a git project root path"
            self.errors.append(
                GitErrorItem(self.local_path_short, InvalidArgument(err_msg), "")
            )
            return
        code = self.change_to_local_repo()
        if code != 0:
            return
        system_home_dir = Path(Globalproperties.allconfig.global_config.filesystem_root_dir)
        if os.path.commonprefix([self.local_path, system_home_dir]) != str(system_home_dir):
            print(f"For security reasons only repositories in the home directory can be managed.")
            return
        is_windows = False
        if sys.platform.startswith('win'):
            is_windows = True   
            os_dir = "win"
        else:
            os_dir = "unix"
        script = os.path.join(Globalproperties.module_dir, "exec", os_dir, "repo_init.sh")
        if not os.path.exists(script):
            return
        if not is_windows and not os.access(script, os.X_OK):
            current_permissions = os.stat(script).st_mode
            os.chmod(script, current_permissions | stat.S_IXUSR)
            print(f"Made {script} executable")
        try:
            run_command(script)
        except subprocess.CalledProcessError:
            self.errors.append(
                GitErrorItem(self.local_path_short, subprocess.CalledProcessError, "")
            )

    def get_remote_repo(self):
        try:
            return self.gitrepo.remote(self.config.remote_repo)
        except ValueError:
            return False
