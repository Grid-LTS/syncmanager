import os
import stat
from typing import Callable, Optional

from git import Repo
from pathlib import Path
import shutil

from .git_base import GitClientBase
from ..util.error import InvalidArgument
from ..util.syncconfig import SyncConfig
import syncmanagerclient.util.globalproperties as globalproperties
import syncmanagerclient.util.system as system

fileextension_filter = [".iml", ".lock"]


class GitArchiveIgnoredFiles(GitClientBase):

    def __init__(self, config : SyncConfig, gitrepo = None):
        super().__init__(gitrepo)
        if config:
            self.set_config(config)
            self.config = config
        self.archive_config = globalproperties.archiveconfig


    def apply(self):
        if not self.local_path.joinpath(".git").resolve().exists():
            raise InvalidArgument(f"{self.local_path} is not a git project root path")
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
                            and not os.path.basename(filename.strip("/").strip("\\")) in self.archive_config.skip_list()]
        files_to_archive = [filename for filename in files_to_archive if not len(set(Path(filename).parts) & set(self.archive_config.skip_directory_list())) > 0]
        files_to_archive = [filename for filename in files_to_archive if not any(filename.endswith(x) for x in self.archive_config.code_file_extensions)]
        files_to_archive = [filename for filename in files_to_archive if is_file_or_dir_and_smaller_than(Path(filename))]

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


def is_file_or_dir_and_smaller_than(path: Path) -> bool:
    max_file_size_for_archiving = globalproperties.archiveconfig.max_archive_filesize_MB * 1024 * 1024
    try:
        if os.path.isfile(path):
            return os.path.getsize(path) <= max_file_size_for_archiving
        if os.path.isdir(path):
            return get_dir_size(path) <= max_file_size_for_archiving
    except OSError as e:
        # File not found or inaccessible
        raise FileNotFoundError(f"File not found or inaccessible: {path}") from e
    else:
        return False

def get_dir_size(path: Path, follow_links: bool = False,
                 onerror: Optional[Callable[[Exception], None]] = None) -> int:
    """
    Compute total size (in bytes) of files under `path`
    - follow_links: if True, os.walk will follow directory symlinks.
    - onerror: optional callback that receives an Exception when os.walk encounters an error.
    - The function records seen (st_dev, st_ino) to avoid double-counting hardlinks or files reached via symlink loops.
    """
    total = 0
    seen_inodes = set()
    for dirpath, dirnames, filenames in os.walk(path, topdown=True, onerror=onerror, followlinks=follow_links):
        for fname in filenames:
            fullpath = os.path.join(dirpath, fname)
            try:
                st = os.stat(fullpath, follow_symlinks=follow_links)
            except OSError as e:
                if onerror:
                    onerror(e)
                continue

            if not stat.S_ISREG(st.st_mode):
                # skip non-regular files (sockets, fifos, etc.)
                continue

            key = (st.st_dev, st.st_ino)
            if key in seen_inodes:
                continue
            seen_inodes.add(key)
            total += st.st_size
    return total