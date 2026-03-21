import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Callable, Optional, List, Any
import re

from git import Repo

from .error import GitErrorItem
from .git_base import GitClientBase
from ..util.error import InvalidArgument
from ..util.globalproperties import Globalproperties
from ..util.syncconfig import SyncConfig

SHARED_ARCHIVE_FOR_ENV = 'shared'


class GitArchiveIgnoredFiles(GitClientBase):
    ignore_markers = [".gitkeep",
                      ".ignoresyncmanager",
                      ".dontarchive"]

    def __init__(self, config: SyncConfig, gitrepo=None):
        super().__init__(config, gitrepo)
        project_root = os.path.basename(self.local_path)
        self.archive_config = Globalproperties.archiveconfig
        system_home_dir = Path(Globalproperties.allconfig.global_config.filesystem_root_dir)
        allconfig = Globalproperties.allconfig
        # the var director folder should usually sit under the $FS_ROOT_DIR/.syncmanager folder
        if len(self.local_path.parents) >= 2:
            common_path = os.path.commonprefix(
                [self.local_path.parents[1], Globalproperties.archive_dir_path.parents[1]])
        else:
            common_path = None
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
        self.archive_project_root = Globalproperties.archive_dir_path.joinpath(self.config.organization,
                                                                               local_path_relative, project_root)
        self.archive_syncenv_root = self.archive_project_root.joinpath(allconfig.sync_env)
        self.archive_syncenv_backup_root = self.archive_project_root.joinpath("syncmanager_backup", allconfig.sync_env)

        self.symlinks = []
        self.directory_registry = dict()
        self.files_to_archive = []

    def apply(self):
        if not self.local_path.exists():
            return
        code = self.change_to_local_repo()
        if code != 0:
            return
        try:
            is_pristine = self.archive_ignored_files()
        except InvalidArgument as err:
            self.errors.append(GitErrorItem(self.local_path_short, err.message, None))
            return
        self.symlink_archived_files_back()

    def archive_ignored_files(self):
        if not self.local_path.joinpath(".git").resolve().exists():
            raise InvalidArgument(f"{self.local_path} is not a git project root path")
        if not self.gitrepo:
            self.gitrepo = Repo(self.local_path)
        self.files_to_archive = self.gitrepo.git.status("--ignored", porcelain=True).split('\n')
        check_for_broken_symlinks = [filename.replace("?? ", "") for filename in self.files_to_archive if
                                     filename.startswith("?? ")]
        check_for_broken_symlinks += self.get_symlinks_committed()
        self.files_to_archive = prune_filenames(
            [filename.replace("!! ", "") for filename in self.files_to_archive if filename.startswith("!! ")])
        self.symlinks = [filename for filename in self.files_to_archive if Path(filename).is_symlink()]
        self.files_to_archive = [filename for filename in self.files_to_archive if not Path(filename).is_symlink()]
        archivable_paths = []
        for file in list(self.files_to_archive):
            if not os.path.isdir(file):
                continue
            if any(x == os.path.basename(file).strip("/") for x in self.archive_config.archivable_dirs):
                archivable_paths.append(file)
                self.files_to_archive.remove(file)
        self.remove_broken_symlinks(self.files_to_archive + self.symlinks + check_for_broken_symlinks)
        for path in self.files_to_archive:
            dirpath = self.local_path / path
            self.remove_broken_symlinks_recursively(dirpath)
        self.filter_ignored_files()
        self.files_to_archive += archivable_paths
        self.remove_broken_symlinks(self.files_to_archive + self.symlinks)
        if not self.files_to_archive:
            return True
        self.extend_git_ignore_file([x for x in self.files_to_archive if Path(x).is_dir()])
        for original_file_rel in self.files_to_archive:
            original_path = Path(original_file_rel)
            if original_path.exists():
                new_path = self.archive_syncenv_root.joinpath(original_file_rel)
                if os.path.exists(new_path):
                    print(f"Archive file {original_file_rel} already exists in new location {new_path}. "
                          f"Move already present file in new location to backup")
                    backup_file_path = self.archive_syncenv_backup_root.joinpath(original_file_rel)
                    backup_file_path.parents[0].mkdir(parents=True, exist_ok=True)
                    shutil.move(str(new_path), str(backup_file_path))
                print(f"Archive file {original_file_rel} in new location {new_path}")
                if self.config.dry_run:
                    continue
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

    def remove_broken_symlinks(self, symlinks):
        for file in symlinks:
            path = Path(file)
            is_stale = path.is_symlink() and not os.path.exists(os.path.realpath(path))
            if not check_if_broken_symlink(path) and not is_stale:
                continue
            if is_stale:
                print(f"{file} is a stale symlink. Delete")
            else:
                print(f"{file} is a broken symlink. Delete")
            path.unlink()
            if file in self.files_to_archive:
                self.files_to_archive.remove(file)

    def filter_ignored_files(self):
        self.files_to_archive = self.filter_ignored_files_based_on_name(self.files_to_archive)
        self.files_to_archive = [filename for filename in self.files_to_archive if
                                 is_file_or_dir_and_smaller_than(Path(filename))]
        for path in list(self.files_to_archive):
            if not os.path.isdir(path):
                continue
            archivable_paths, symlinked_paths = self.find_archivable_file_paths(Path(path))
            self.symlinks += symlinked_paths
            if len(archivable_paths) == 1 and archivable_paths[0].relative_to(self.local_path) == path:
                continue
            # if the path is a directory but contains files or dirs that must not be archived,
            self.files_to_archive.remove(path)
            # only archive the eligible paths under it
            self.files_to_archive += [x.relative_to(self.local_path) for x in archivable_paths]
        # we do not archive files that live in git-managed directories, having ignore-marker file like .gitkeep, because these directories
        # are operational and contain only short-term or processed data
        for filename in list(self.files_to_archive):
            parent_dir = Path.resolve(Path(filename).parent)
            while parent_dir != self.local_path and parent_dir != self.local_path.parent:
                if any((parent_dir / ignore_marker).exists() for ignore_marker in self.__class__.ignore_markers):
                    self.files_to_archive.remove(filename)
                    break
                parent_dir = Path.resolve(parent_dir.parent)

    def filter_ignored_files_based_on_name(self, files_to_archive: List[str]):
        return [filename for filename in files_to_archive if
                (Path(filename).is_dir() and self.is_eligible_directory(filename))
                or (Path(filename).is_file() and self.is_eligible_file(filename))
                ]

    def is_eligible_file(self, filename) -> bool:
        return (self.is_eligible_directory(filename)
                and not any(filename.endswith(x) for x in self.archive_config.code_file_extensions))

    def is_eligible_directory(self, filename) -> bool:
        return (not filename in self.symlinks
                and not any(x.match(filename) for x in self.archive_config.skip_regex_pattern)
                and not os.path.basename(filename) in self.archive_config.skip_list()
                and not len(set(Path(filename).parts) & set(self.archive_config.skip_directory_list())) > 0)

    def symlink_archived_files_for_env(self, archive_path: Path, revert=False):
        if not archive_path.exists():
            return
        archive_path = archive_path.resolve()
        for root, dirs, files in os.walk(archive_path):
            if archive_path.parent == Path(root):
                continue
            relpath = Path(root).relative_to(archive_path)
            if Path(root) != archive_path:
                would_be_link_location = self.local_path.joinpath(relpath)
                source_location = archive_path.joinpath(relpath)
                is_created = self.create_symlink(would_be_link_location, source_location, _revert=revert)
                if is_created:
                    dirs[:] = []
            for filename in files:
                file_rel_path = relpath.joinpath(filename)
                file_link_parent = self.local_path.joinpath(relpath)
                if not file_link_parent.exists():
                    file_link_parent.mkdir(parents=True, exist_ok=True)
                source_location = Path(root).joinpath(filename)
                would_be_link_location = self.local_path.joinpath(file_rel_path)
                self.create_symlink(would_be_link_location, source_location, _revert=revert)

    def create_symlink(self, would_be_link_location: Path, source_location: Path, _revert=False):
        try:
            if not source_location.exists():
                return True
        except OSError as e:
            try:
                print(f"Corrupted state. Source location {source_location} is a broken link. Remove")
                os.unlink(str(source_location))
            except OSError as e:
                print(f"Cannot remove {source_location}. Please repair manually.")
                return True
        if source_location.is_file():
            fs_type = "file"
            target_is_directory = False
        else:
            fs_type = "directory"
            target_is_directory = True
        if not _revert:
            if not would_be_link_location.exists() and not would_be_link_location.is_symlink():
                print(f"Create {fs_type} symlink at {would_be_link_location} pointing to {source_location}")
                if not self.config.dry_run:
                    would_be_link_location.symlink_to(source_location, target_is_directory=target_is_directory)
                return True
            return False
        if would_be_link_location.exists() and would_be_link_location.is_symlink():
            print(f"Revert {fs_type} symlink at {would_be_link_location}, pointing to {source_location}")
            if not self.config.dry_run:
                os.unlink(would_be_link_location)
                shutil.move(source_location, would_be_link_location)
                if not os.listdir(str(source_location.parent.absolute())):
                    shutil.rmtree(str(source_location.parent.absolute()))
            return True
        return False

    def symlink_archived_files_back(self, revert=False):
        if not self.archive_project_root.exists():
            return
        envs = os.listdir(self.archive_project_root)
        if not envs or not SHARED_ARCHIVE_FOR_ENV in envs:
            return
        if revert:
            self.symlink_archived_files_for_env(self.archive_syncenv_root, False)
        self.symlink_archived_files_for_env(self.archive_syncenv_root, revert)

    def get_unstaged_files(self):
        """
        not used, but kept for further repo pruning
        :return:
        """
        unstaged_files = [x.replace("?? ", "") for x in self.gitrepo.git.status(porcelain=True).split('\n') if
                          x.startswith("?? ")]
        if '' in unstaged_files:
            unstaged_files.remove('')

    def find_archivable_file_paths(self, path: Path, max_depth: Optional[int] = None,
                                   follow_symlinks: bool = False) -> tuple[list[Path], list[Any]] | tuple[
        list[Path], list[Path]]:
        if not path.is_dir():
            return [path], []
        archivable_paths = self.find_archivable_files(path, max_depth=max_depth, follow_symlinks=follow_symlinks)
        # consolidate
        symlinked_paths: List[Path] = []
        for path in list(archivable_paths):
            if path.is_symlink():
                symlinked_paths.append(path)
                archivable_paths.remove(path)
                continue
            if any(parent_path in archivable_paths for parent_path in path.parents):
                archivable_paths.remove(path)
        return archivable_paths, symlinked_paths

    def find_archivable_files(self, path: Path, max_depth: Optional[int] = None,
                              follow_symlinks: bool = False) -> List[Path]:
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
        path_registry = []
        skip_directories = []
        # Use absolute path for predictable parent traversal (avoid relative surprises)
        p = path.resolve()
        if not p.exists() or not p.is_dir():
            return []
        # Use os.walk to allow pruning `dirs` for depth-limiting and permission handling.
        for dirpath, dirnames, filenames in os.walk(str(p), topdown=True, followlinks=follow_symlinks):
            # if any(x in Path(dirpath).parents for x in skip_directories):
            #    continue
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
                if current.parent in path_registry:
                    path_registry.remove(current.parent)
                dirnames[:] = []
                continue
            git_entry = current / ".git"
            try:
                if git_entry.exists():
                    if current.parent in path_registry:
                        path_registry.remove(current.parent)
                    dirnames[:] = []
                    continue
                # check if bare git repo
                # add more conditions
                if (current / "HEAD").exists() and (current / "refs").exists() and (current / "config").exists():
                    if current.parent in path_registry:
                        path_registry.remove(current.parent)
                    dirnames[:] = []
                    continue
                if any((current / ignore_marker).exists() for ignore_marker in self.__class__.ignore_markers):
                    if current.parent in path_registry:
                        path_registry.remove(current.parent)
                    dirnames[:] = []
                    continue
                if not self.filter_ignored_files_based_on_name([str(current.relative_to(self.local_path))]):
                    if current.parent in path_registry:
                        path_registry.remove(current.parent)
                    dirnames[:] = []
                    continue
            except PermissionError:
                # skip directories we cannot stat, but continue searching other branches
                dirnames[:] = []
                continue
            directory_is_eligible = True
            dir_rel_path = Path(dirpath).relative_to(self.local_path)
            if filenames:
                okay_files = self.ignored(self.filter_ignored_files_based_on_name(prune_filepaths([
                    dir_rel_path.joinpath(filename) for filename in filenames])))
                path_registry += [self.local_path.joinpath(file) for file in okay_files]
                directory_is_eligible = len(okay_files) == len(filenames)
            if directory_is_eligible and self.is_ignored(str(dir_rel_path)):
                path_registry.append(current)
        return path_registry

    def ignored(self, filepaths: List[str]) -> List[str]:
        if not filepaths:
            return []
        return self.gitrepo.ignored(*filepaths)

    def is_ignored(self, filepath: str) -> bool:
        ignored_list = self.gitrepo.ignored(filepath)
        return bool(ignored_list)

    def remove_broken_symlinks_recursively(self, path: Path):
        for dirpath, dirnames, filenames in os.walk(str(path), topdown=True, followlinks=True):
            # we don't follow symlinks recursively
            if self.check_and_remove_broken_symlink(Path(dirpath)):
                dirnames[:] = []
                continue
            for name in filenames + dirnames:
                current = Path(dirpath) / name
                self.check_and_remove_broken_symlink(current)

    def check_and_remove_broken_symlink(self, current: Path):
        try:
            if not current.is_symlink():
                return False
            current.is_dir()  # forces to resolve target file and sees if symlink is broken
        except OSError as e:
            print(f"Target of committed symlink at {str(current)} cannot be resolved. Remove")
            try:
                os.unlink(str(current))
            except OSError:
                pass
        self.remove_broken_symlinks([current])
        return True

    def get_symlinks_committed(self):
        head = self.gitrepo.head.commit
        symlinks = []
        for blob in head.tree.traverse():
            # blob is a git.Tree or git.Blob; the latter has a .mode attribute
            # and .path gives the relative path
            if blob.type == 'blob' and stat.S_ISLNK(blob.mode):
                try:
                    Path(blob.path).readlink()
                except OSError as e:
                    print(f"Target of committed symlink at {blob.path} cannot be resolved. Remove")
                    try:
                        os.unlink(blob.path)
                    except OSError:
                        pass
                    continue
                try:
                    if Path(blob.path).readlink().relative_to(Globalproperties.archive_dir_path):
                        symlinks.append(blob.path)
                except ValueError as e:
                    pass
                except OSError as e:
                    print(f"Cannot resolve target of symlink at {blob.path}")
        return symlinks

    def extend_git_ignore_file(self, ignored_directories):
        """
        Extend .gitignore with directories that don't have matching patterns.
        
        For each directory in ignored_directories:
        1. Scan .gitignore files in the item's directory and parent directories for matching patterns (based on basename)
        2. If no match found, append the full relative path to the nearest .gitignore file
        
        Args:
            ignored_directories: List of directory paths (strings)
        """
        directories_to_add = []

        for directory in ignored_directories:
            directory_path = Path(directory)
            basename = directory_path.name

            gitignore_files = self._find_gitignore_files_for_path(directory_path)

            matched = False
            for gitignore_path in gitignore_files:
                existing_patterns = self._read_gitignore_patterns(gitignore_path)

                for pattern in existing_patterns:
                    pattern_stripped = pattern.rstrip('/')

                    if pattern.endswith('/') and pattern_stripped == basename:
                        continue

                    if self._matches_gitignore_pattern(pattern_stripped, basename):
                        matched = True
                        break

                if matched:
                    break

            if not matched:
                directories_to_add.append((directory, gitignore_files[0] if gitignore_files else None))

        for directory, gitignore_path in directories_to_add:
            if gitignore_path is None:
                gitignore_path = self.local_path / '.gitignore'

            # Calculate relative path from .gitignore directory to target directory
            gitignore_dir = gitignore_path.parent
            directory_absolute = (self.local_path / directory).resolve()
            entry = str(directory_absolute.relative_to(gitignore_dir.resolve()))
            normalized_entry = self._normalize_gitignore_entry(entry)

            # Check if basename already exists (keeping it exactly as written in .gitignore)
            directory_basename = Path(normalized_entry).name
            existing_basenames = self._read_gitignore_patterns(gitignore_path)
            if directory_basename not in [x.split('/')[-1] for x in existing_basenames]:
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + normalized_entry + '\n')

    def _find_gitignore_files_for_path(self, item_path):
        """
        Find all .gitignore files from the item's directory up to the repository root.
        Returns ordered list from nearest to furthest.
        
        Args:
            item_path: Path to the directory item (relative to repository root)
        
        Returns:
            List of Path objects pointing to .gitignore files
        """
        gitignore_files = []

        current_path = (self.local_path / item_path).resolve()
        repo_root = self.local_path.resolve()

        while current_path >= repo_root:
            gitignore_path = current_path / '.gitignore'
            if gitignore_path.exists():
                gitignore_files.append(gitignore_path)

            if current_path == repo_root:
                break

            current_path = current_path.parent

        return gitignore_files

    def _read_gitignore_patterns(self, gitignore_path):
        """
        Read patterns from a .gitignore file.
        
        Args:
            gitignore_path: Path to .gitignore file
        
        Returns:
            List of pattern strings (filtered for comments, empty lines, and negation patterns)
        """
        patterns = []

        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.rstrip('\r\n')
                    if not line:
                        continue
                    if line.startswith('#'):
                        continue
                    if line.startswith('!'):
                        continue
                    patterns.append(line)

        return patterns

    def _read_gitignore_entries(self, gitignore_path):
        """
        Read all entries from a .gitignore file for duplicate checking.
        
        Args:
            gitignore_path: Path to .gitignore file
        
        Returns:
            Set of normalized entry strings
        """
        entries = set()

        for entry in self._read_gitignore_patterns(gitignore_path):
            normalized_entry = self._normalize_gitignore_entry(entry)
            entries.add(normalized_entry)
        return entries

    def _normalize_gitignore_entry(self, entry):
        normalized = entry.replace('\\', '/')
        if normalized.startswith('./'):
            normalized = normalized[2:]
        normalized = normalized.rstrip('/')
        return normalized

    def _matches_gitignore_pattern(self, pattern, name):
        if pattern.startswith('/'):
            pattern = pattern[1:]
        regex_pattern = self._gitignore_pattern_to_regex(pattern)
        return bool(regex_pattern.fullmatch(name))

    def _gitignore_pattern_to_regex(self, pattern):
        regex_parts = []
        in_char_class = False

        i = 0
        while i < len(pattern):
            char = pattern[i]

            if char == '*':
                regex_parts.append('[^/]*')
            elif char == '?':
                regex_parts.append('[^/]')
            elif char == '[':
                if i + 1 < len(pattern) and pattern[i + 1] == '!':
                    regex_parts.append('[^')
                    i += 1
                else:
                    regex_parts.append('[')
                in_char_class = True
            elif char == ']' and in_char_class:
                regex_parts.append(']')
                in_char_class = False
            elif char in '.^$+()|\\':
                if not in_char_class:
                    regex_parts.append('\\' + char)
                else:
                    regex_parts.append(char)
            else:
                regex_parts.append(re.escape(char) if not in_char_class else char)

            i += 1

        regex = '^' + ''.join(regex_parts) + '$'
        return re.compile(regex)


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


def prune_filenames(files_to_archive: List[str]):
    files = [filename.strip("/").strip("\\").strip(os.path.pathsep) for filename in files_to_archive]
    return files


def prune_filepaths(files_to_archive: List[Path]):
    return prune_filenames([str(x) for x in files_to_archive])
