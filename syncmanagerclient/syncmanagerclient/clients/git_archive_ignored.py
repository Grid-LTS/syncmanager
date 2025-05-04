import os

from git import Repo, GitCommandError
from pathlib import Path

from .git_base import GitClientBase
from ..util.syncconfig import SyncConfig

filter_list = [".DS_Store", "__pycache__", ".venv" , "venv", ".pytest_cache", ".DS_Store", "dist", ".idea"]
fileextension_filter = [".iml"]

class Gitc(GitClientBase):

    def __init__(self, config : SyncConfig, gitrepo = None):
        super().__init__(gitrepo)
        if config:
            self.set_config(config)
            self.config = config

    def apply(self):
        if not self.gitrepo:
            self.gitrepo = Repo(self.local_path)
        ignored_files = self.gitrepo.git.status("--ignored", porcelain=True).split('\n')
        ignored_files = [filename.replace("!! ", "") for filename in ignored_files if filename.startswith("!! ")]
        ignored_files = [filename for filename in ignored_files if not Path(filename).is_symlink() and not any(filename.endswith(x) for x in fileextension_filter)
                         and not os.path.basename(filename.strip("/").strip("\\")) in filter_list ]
        print(ignored_files)