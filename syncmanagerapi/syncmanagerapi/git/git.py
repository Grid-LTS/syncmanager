import os
import os.path as osp
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

    @staticmethod
    def get_bare_repo_fs_path(server_path_relative):
        fs_root_dir = current_app.config['FS_ROOT']
        return osp.join(osp.join(fs_root_dir, 'git'), server_path_relative)
