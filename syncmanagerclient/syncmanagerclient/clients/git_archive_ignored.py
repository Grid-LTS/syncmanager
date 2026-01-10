import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Callable, Optional
import re

from git import Repo

from .error import GitErrorItem
from .git_base import GitClientBase
from ..util.error import InvalidArgument
from ..util.globalproperties import Globalproperties
from ..util.syncconfig import SyncConfig
from ..util.system import home_dir

DEFAULT_SYNC_ENV = 'default'


class GitArchiveIgnoredFiles(GitClientBase):

    def __init__(self, config: SyncConfig, gitrepo=None):
        super().__init__(gitrepo)
        if config:
            self.set_config(config)
            self.config = config
        project_root = os.path.basename(self.local_path)
        self.archive_config = Globalproperties.archiveconfig
        system_home_dir = Path(home_dir)
        allconfig = Globalproperties.allconfig
        # the var director folder should usually sit under the $HOME/.syncmanager folder
        common_path = os.path.commonprefix([self.local_path.parents[1], Globalproperties.archive_dir_path.parents[1]])
        if common_path and os.path.commonprefix([common_path, system_home_dir]) != common_path:
            # mostly for e2e test environment
            local_path_relative = self.local_path.parents[0].relative_to(common_path)
        else:
            if sys.platform.startswith("win") and Path(system_home_dir).parts[0] != \
                    Path(self.local_path.parents[0]).parts[0]:
                local_path_relative = Path(*Path(self.local_path.parents[0]).parts[1:])
            else:
                local_path_relative = self.local_path.parents[0].relative_to(system_home_dir)
        # normalize to be OS independent
        local_path_relative = Path(*[part.lower() for part in local_path_relative.parts])
        self.archive_project_root = Globalproperties.archive_dir_path.joinpath(allconfig.organization,
                                                                               local_path_relative, project_root)
        self.archive_default_root = self.archive_project_root.joinpath(DEFAULT_SYNC_ENV)
        self.archive_syncenv_root = self.archive_project_root.joinpath(allconfig.sync_env)

    def apply(self):
        if not self.local_path.exists():
            return
        try:
            is_pristine = self.archive_ignored_files()
        except InvalidArgument as err:
            self.errors.append(GitErrorItem(self.local_path_short, err.message, None))
            return
        if is_pristine:
            self.symlink_archived_files_back()

    def archive_ignored_files(self):
        if not self.local_path.joinpath(".git").resolve().exists():
            raise InvalidArgument(f"{self.local_path} is not a git project root path")
        if not self.gitrepo:
            self.gitrepo = Repo(self.local_path)
        files_to_archive = self.gitrepo.git.status("--ignored", porcelain=True).split('\n')
        files_to_archive = [filename.replace("!! ", "").strip("/").strip("\\").strip(os.path.pathsep) for filename in
                            files_to_archive if filename.startswith("!! ")]
        symlinks = [filename for filename in files_to_archive if Path(filename).is_symlink()]
        files_to_archive = [filename for filename in files_to_archive if not filename in symlinks and not any(
            x.match(filename) for x in self.archive_config.skip_regex_pattern)
                            and not os.path.basename(
            filename) in self.archive_config.skip_list()]
        files_to_archive = [filename for filename in files_to_archive if
                            not len(set(Path(filename).parts) & set(self.archive_config.skip_directory_list())) > 0]
        files_to_archive = [filename for filename in files_to_archive if
                            not any(filename.endswith(x) for x in self.archive_config.code_file_extensions)]
        files_to_archive = [filename for filename in files_to_archive if
                            not directory_contains_git_repo(Path(filename))
                            and is_file_or_dir_and_smaller_than(Path(filename))]
        # we do not archive files that live in git-managed directories, having .gitkeep file, because these directory
        # are operational and contain only short-term or processed data
        files_to_archive = [filename for filename in files_to_archive if
                            not (Path(filename).parent / ".gitkeep").exists()]

        for file in list(files_to_archive + symlinks):
            path = Path(file)
            is_stale = path.is_symlink() and not os.path.exists(os.path.realpath(path))
            if not check_if_broken_symlink(path) and not is_stale:
                continue
            if is_stale:
                print(f"{file} is a stale symlink. Delete")
            else:
                print(f"{file} is a broken symlink. Delete")
            path.unlink()
            if file in files_to_archive:
                files_to_archive.remove(file)

        if not files_to_archive:
            return True

        for original_file_rel in files_to_archive:
            original_path = Path(original_file_rel)
            if original_path.exists():
                new_path = self.archive_default_root.joinpath(original_file_rel)
                if os.path.exists(new_path):
                    new_path = self.archive_syncenv_root.joinpath(original_file_rel)
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
        return False

    def symlink_archived_files_for_env(self, archive_path: Path):
        if not archive_path.exists():
            return
        skip_dirs = []  # contains directories that are already symlinked
        for root, dirs, files in os.walk(archive_path):
            relpath = Path(root).relative_to(archive_path)
            if relpath in skip_dirs or relpath.parent in skip_dirs:
                if relpath.parent in skip_dirs:
                    skip_dirs.append(relpath)
                continue
            for dirname in dirs:
                dir_rel_path = relpath.joinpath(dirname)
                would_be_link_location = self.local_path.joinpath(dir_rel_path)
                if not would_be_link_location.exists() and not would_be_link_location.is_symlink():
                    source_location = Path(root).joinpath(dirname)
                    would_be_link_location.symlink_to(source_location, target_is_directory=True)
                    print(f"Create directory symlink at {would_be_link_location} pointing to {source_location}")
                elif would_be_link_location.is_symlink():
                    skip_dirs.append(dir_rel_path)
            for filename in files:
                file_rel_path = relpath.joinpath(filename)
                if not self.local_path.joinpath(file_rel_path).exists():
                    would_be_link_location = self.local_path.joinpath(file_rel_path)
                    source_location = Path(root).joinpath(filename)
                    print(f"Create file symlink at {would_be_link_location} pointing to {source_location}")
                    would_be_link_location.symlink_to(source_location)

    def symlink_archived_files_back(self):
        if not self.archive_project_root.exists():
            #print(f"No archive registered for repo {self.local_path_short}")
            return
        envs = os.listdir(self.archive_project_root)
        if not envs or not DEFAULT_SYNC_ENV in envs:
            return
        self.symlink_archived_files_for_env(self.archive_syncenv_root)
        self.symlink_archived_files_for_env(self.archive_default_root)


    def get_unstaged_files(self):
        """
        not used, but kept for further repo pruning
        :return:
        """
        unstaged_files = [x.replace("?? ", "") for x in self.gitrepo.git.status(porcelain=True).split('\n') if x.startswith("?? ")]
        if '' in unstaged_files:
            unstaged_files.remove('')


def directory_contains_git_repo(path: Path):
    if not path.is_dir():
        return False
    return has_git_repo_under(path)


def find_git_repos_under(path: Path, max_depth: Optional[int] = None,
                         follow_symlinks: bool = False) -> Optional[Path]:
    """
    Recursively search downward from `path` for directories that contain a ".git" entry.
    Also include directories with .gitkeep entry, since these directories are managed by git and should also not be
    archived

    - `path`: directory (or file; file => its parent directory is used) to start the search from.
    - `max_depth`: if provided, limits recursion depth (0 means only the start directory).
                 Depth is measured in directory levels below the start directory.
    - `follow_symlinks`: whether to follow directory symlinks while recursing (defaults False).

    Returns a list of Path objects pointing to directories that contain a ".git" entry
    (the directory which itself contains ".git"). If none found, returns an empty list.
    """
    # Use absolute path for predictable parent traversal (avoid relative surprises)
    p = path.resolve()
    if not p.exists() or not p.is_dir():
        return None

    # Use os.walk to allow pruning `dirs` for depth-limiting and permission handling.
    for dirpath, dirnames, filenames in os.walk(str(p), topdown=True, followlinks=follow_symlinks):
        try:
            # depth relative to root
            rel = os.path.relpath(dirpath, str(p))
        except ValueError:
            # In weird cases (different mounts / windows UNC) fallback to full parts count
            rel = dirpath
        depth = 0 if rel == '.' else rel.count(os.sep) + 1  # number of levels below root

        # If max_depth specified and we are at or past it, prune further descent.
        if max_depth is not None and depth > max_depth:
            dirnames[:] = []
            continue
        if max_depth is not None and depth == max_depth:
            # don't descend further from this level
            dirnames[:] = []

        current = Path(dirpath)
        if str(current).endswith(".git"):
            return current
        git_entry = current / ".git"
        try:
            if git_entry.exists():
                return git_entry
            # check if bare git repo
            # add more conditions
            if (current / "HEAD").exists() and (current / "refs").exists() and (current / "config").exists():
                return current
            if (current / ".gitkeep").exists():
                return current

        except PermissionError:
            # skip directories we cannot stat, but continue searching other branches
            dirnames[:] = []
            continue

    return None


_RE = re.compile(r'\AXSym\r?\n[0-9]{4}\r?\n[0-9A-Fa-f]{32}\r?\n/(?:[^/\x00]+(?:/(?!/)[^/\x00]+)*)/?\r?\Z')


def check_if_broken_symlink(path: Path):
    """
    Return True if the file at `path` contains exactly the format:

      XSym
      <4 digits>
      <32 hex chars>
      <absolute filesystem path>

    - accepts LF or CRLF line endings
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        # Could raise or return False depending on desired behavior
        return False

    return bool(_RE.match(text))


def has_git_repo_under(path: Path,
                       max_depth: Optional[int] = None,
                       follow_symlinks: bool = False) -> Optional[Path]:
    """
    Convenience wrapper that returns the first repository found (or None).
    """
    repo = find_git_repos_under(path, max_depth=max_depth, follow_symlinks=follow_symlinks)
    return repo is not None


def is_file_or_dir_and_smaller_than(path: Path) -> bool:
    max_file_size_for_archiving = Globalproperties.archiveconfig.max_archive_filesize_MB * 1024 * 1024
    try:
        if path.is_file():
            return os.path.getsize(path) <= max_file_size_for_archiving
        if path.is_dir():
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
