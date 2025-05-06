import os
import os.path as osp
import shutil
import pathlib

from git import Repo
from flask import current_app

from ..error import FsConflictError


class GitRepoFs:
    gitrepo_entity = None
    gitrepo_path = ''

    def __init__(self, gitrepo_entity):
        self.gitrepo_entity = gitrepo_entity
        self.gitrepo_path = GitRepoFs.get_bare_repo_fs_path(gitrepo_entity.server_path_rel)

    def create_bare_repo(self):
        # first check if directory exists
        if os.path.exists(self.gitrepo_path):
            if os.path.isfile(self.gitrepo_path):
                raise FsConflictError('Upstream repository could not be created', self.gitrepo_entity.server_path_rel)
            else:
                return True
        else:
            oldmask = os.umask(0o002)
            os.makedirs(self.gitrepo_path)
            os.umask(oldmask)
        git_subdir = osp.join(self.gitrepo_path, '.git')
        if os.path.exists(git_subdir):
            return True
        Repo.init(self.gitrepo_path, bare=True)
        return True

    def move_repo(self, target_path_rel):
        target_path = GitRepoFs.get_bare_repo_fs_path(target_path_rel)
        if os.path.exists(target_path):
            raise FsConflictError('Upstream repository could not be moved', self.gitrepo_entity.server_path_rel,
                                      target_path)
        oldmask = os.umask(0o002)
        shutil.move(self.gitrepo_path, target_path)
        GitRepoFs.remove_empty_dir_tree_recursively(self.gitrepo_entity.server_path_rel)
        os.umask(oldmask)
        return True

    @staticmethod
    def remove_first_path_part(path):
        p = pathlib.Path(path)
        return p.relative_to(*p.parts[:1])

    @staticmethod
    def remove_last_path_part(path):
        p = pathlib.Path(path)
        return p.parent

    @staticmethod
    def get_bare_repo_fs_path(server_path_relative):
        fs_root_dir = current_app.config['FS_ROOT']
        return osp.join(osp.join(fs_root_dir, 'git'), server_path_relative)

    @staticmethod
    def remove_empty_dir_tree_recursively(dir_path):
        p = pathlib.Path(dir_path)
        if len(p.parts) < 2:
            return None
        absolute_path = GitRepoFs.get_bare_repo_fs_path(dir_path)
        if os.path.exists(absolute_path):
            files = os.listdir(absolute_path)
            if len(files) != 0:
                return None
            os.rmdir(absolute_path)
        GitRepoFs.remove_empty_dir_tree_recursively(GitRepoFs.remove_last_path_part(dir_path))

