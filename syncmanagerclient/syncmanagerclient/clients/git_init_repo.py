import os
import subprocess
import sys
from pathlib import Path

from .error import GitErrorItem
from .git_base import GitClientBase
from ..util.error import InvalidArgument
from ..util.syncconfig import SyncConfig
from ..util.system import change_dir, run_command
import syncmanagerclient.util.globalproperties as globalproperties
import syncmanagerclient.util.system as system

fileextension_filter = [".iml", ".lock"]


class GitInitRepo(GitClientBase):

    def __init__(self, config: SyncConfig, gitrepo=None):
        super().__init__(gitrepo)
        if config:
            self.set_config(config)
            self.config = config

    def apply(self):
        if not self.local_path.joinpath(".git").resolve().exists():
            err_msg = f"{self.local_path} is not a git project root path"
            self.errors.append(
                GitErrorItem(self.local_path_short, InvalidArgument(err_msg), "")
            )
            return
        system_home_dir = Path(system.home_dir)
        if os.path.commonprefix([self.local_path, system_home_dir]) != str(system_home_dir):
            print(f"For security reasons only repositories in the home directory can be managed.")
            return
        change_dir(self.local_path)
        if sys.platform.startswith('win'):
            os_dir = "win"
        else:
            os_dir = "unix"
        script = os.path.join(globalproperties.module_dir, "exec", os_dir, "repo_init.sh")
        try:
            run_command(script)
        except subprocess.CalledProcessError:
            self.errors.append(
                GitErrorItem(self.local_path_short, subprocess.CalledProcessError, "")
            )
