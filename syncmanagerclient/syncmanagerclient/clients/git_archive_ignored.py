import os
from xml.dom import InvalidStateErr

from git import Repo
from pathlib import Path
import shutil

from .git_base import GitClientBase
from ..util.syncconfig import SyncConfig
import syncmanagerclient.util.globalproperties as globalproperties
import syncmanagerclient.util.system as system

build_and_cached_dirs = ["__pycache__", ".pytest_cache", ".gradle", "gradle", "build", "out", "target"]
dependency_dirs = [".venv",  "venv", "dist", "node_modules"]
ignore_directories = [".idea", "lib", ".temp", "tmp", "temp", ".tmp","logs"]
build_artefacts = ["gradle-wrapper.jar"]
optional_files = ["access.log"]
environment_files =  [".DS_Store"]
code_file_extensions = [
    "js", "jsx","js.map", "ts", "tsx", "py", "pyc", "java", "php"
]
filter_list =  dependency_dirs + environment_files + optional_files + build_artefacts
directory_list = build_and_cached_dirs + ignore_directories
fileextension_filter = [".iml", ".lock"]

class GitArchiveIgnoredFiles(GitClientBase):

    def __init__(self, config : SyncConfig, gitrepo = None):
        super().__init__(gitrepo)
        if config:
            self.set_config(config)
            self.config = config

    def apply(self):
        if not self.local_path.joinpath(".git").resolve().exists():
            raise InvalidStateErr(f"{self.local_path} is not a git project root path")
        system_home_dir = Path(system.home_dir)
        if os.path.commonprefix([self.local_path, system_home_dir]) != str(system_home_dir):
            print(f"For security reasons only repositories in the home directory can be managed.")
            return
        project_root = os.path.basename(self.local_path)
        if not self.gitrepo:
            self.gitrepo = Repo(self.local_path)
        files_to_archive = self.gitrepo.git.status("--ignored", porcelain=True).split('\n')
        files_to_archive = [filename.replace("!! ", "") for filename in files_to_archive if filename.startswith("!! ")]
        files_to_archive = [filename for filename in files_to_archive if not Path(filename).is_symlink() and not any(filename.endswith(x) for x in fileextension_filter)
                         and not os.path.basename(filename.strip("/").strip("\\")) in filter_list ]
        files_to_archive = [filename for filename in files_to_archive if not len(set(Path(filename).parts) & set(directory_list)) > 0 ]
        files_to_archive = [filename for filename in files_to_archive if not any(filename.endswith(x) for x in code_file_extensions)]

        allconfig = globalproperties.allconfig

        # the var director folder should usually sit under the $HOME/syncmanager folder
        # if this is not the case we must prevent overlong paths
        common_path = os.path.commonprefix([self.local_path.parents[1], globalproperties.archive_dir_path.parents[1]])
        if common_path and os.path.commonprefix([common_path, system_home_dir]) != common_path:
            # mostly for e2e test environment
            local_path_relative =  self.local_path.parents[0].relative_to(common_path)
        else:
            local_path_relative =  self.local_path.parents[0].relative_to(system_home_dir)
        archive_project_root = globalproperties.archive_dir_path.joinpath(allconfig.organization,
                                                                          local_path_relative,
                                                                          project_root, allconfig.sync_env)
        for original_file_rel in files_to_archive:
            original_path = Path(original_file_rel)
            if original_path.exists():
                new_path = archive_project_root.joinpath(original_file_rel)
                print(f"Archive file {original_file_rel} in new location {new_path}")
                new_path.parents[0].mkdir(parents=True, exist_ok=True)
                shutil.move(str(original_path), str(new_path))
                # Create symlink at the original location pointing to the new location
                try:
                    original_path.symlink_to(new_path)
                except Exception as e:
                    # roll back
                    shutil.move(str(new_path), str(original_path))
                    if isinstance(e, OSError):
                        print(f"Activate developer mode to allow creation of symlinks. Error : {e}")
                    else:
                        print(f"Unexpected error: {e}")