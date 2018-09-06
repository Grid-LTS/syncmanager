import os
from git import Repo
from ..util.system import run, change_dir, sanitize_path

from . import ACTION_PULL, ACTION_PUSH, ACTION_DELETE


class GitClientSync:
    def __init__(self, action):
        self.action = action

    def set_config(self, config, force):
        self.local_path_short = config.get('source', None)
        self.local_path = sanitize_path(self.local_path_short)
        self.local_reponame = os.path.basename(self.local_path)
        self.remote_reponame = config.get('remote_repo', None)
        self.remote_path = config.get('url', None)
        self.settings = config.get('settings', None)
        self.force = force

    def apply(self, **kwargs):
        start_dir = os.getcwd()
        code = self.change_to_local_repo()
        if code != 0:
            return
        self.gitrepo = Repo(self.local_path)
        self.remote_gitrepo = self.gitrepo.remote(self.remote_reponame)
        # checkout master branch
        if hasattr(self.gitrepo.heads, 'master'):
            self.gitrepo.heads.master.checkout()
        if self.action == ACTION_PULL or self.action == ACTION_PUSH:
            # PULL and PUSH are the only actions that happen online, with an actual sync with the remote repo
            # fetch and prune all branches in local repo
            code = self.git_fetch(True)
            # delete local branches with with the remote tracking branches 'gone',
            self.cleanup_orphaned_local_branches()
        if self.action == ACTION_PULL:
            self.sync_pull()
        elif self.action == ACTION_PUSH:
            self.sync_push()
        elif self.action == ACTION_DELETE:
            self.delete_branch(**kwargs)
        change_dir(start_dir)

    def sync_pull(self):
        # only consider branches of the remote repo with a tracking relationship
        tracked_remotes = []
        for branch in self.gitrepo.heads:
            remote_branch = branch.tracking_branch()
            if not remote_branch:
                continue
            expected_branch, repo = self.get_branch_name_and_repo_from_remote_path(str(remote_branch))
            if repo != self.remote_reponame:
                continue
            tracked_remotes.append(remote_branch)
            if expected_branch != str(branch):
                print('Local branch {} and remote branch {} do not match. Skip'.format(branch, expected_branch))
                continue
            branch.checkout()
            git = self.gitrepo.git
            if self.force:
                print(branch)
                # force pull of the remote repo
                git.reset('--hard', str(remote_branch))
                print('Force reset of local branch \'{0}\' to remote ref.'.format(str(branch)))
            else:
                # just pull all updates
                out = git.pull(None, with_stdout=True)
                print(out)
                break

        # checkout a local branch for all remote refs not being tracked
        # remote refs in the shape origin/feature/my-remote/
        for remote_ref in self.remote_gitrepo.refs:
            name, repo = self.get_branch_name_and_repo_from_remote_path(str(remote_ref))
            if not remote_ref in tracked_remotes and not name == 'HEAD':
                print('Set up local tracking branch for {}'.format(str(remote_ref)))
                self.create_local_branch_from_remote(remote_ref)
                # remote ref does not have a local tracking branch

        # finally checkout master branch
        self.gitrepo.heads.master.checkout()
        print('')

    def delete_branch(self, **kwargs):
        path = kwargs.get('path', None)
        if not path:
            print('Error. No branch given.')
            exit(1)
        print('Deleting branch {}.'.format(path))
        out = self.gitrepo.delete_head(path)
        if out:
            print(out)

    def cleanup_orphaned_local_branches(self):
        # get all branches that have a remote tracking branch, that is not part of the remote refs anymore
        for branch in self.gitrepo.heads:
            # do not delete master
            if (str(branch) == 'master' or str(branch) == 'HEAD'):
                continue
            remote_tracking = branch.tracking_branch()
            parts = str(remote_tracking).split('/')
            remote_repo = parts[0]
            # skip if the tracking branch belongs to another remote repo
            if remote_repo != str(self.remote_gitrepo):
                continue
            if remote_tracking and not remote_tracking in self.remote_gitrepo.refs:
                print('Delete orphaned branch \'{0}\''.format(branch))
                self.gitrepo.delete_head(branch)

    def create_local_branch_from_remote(self, remote_branch):
        local_branch, repo = self.get_branch_name_and_repo_from_remote_path(str(remote_branch))
        if not str(repo) == str(self.remote_reponame):
            return None
        self.gitrepo.create_head(local_branch, remote_branch)  # create local branch from remote
        getattr(self.gitrepo.heads, str(local_branch)).set_tracking_branch(remote_branch)

    def sync_push(self):
        git = self.gitrepo.git
        # find all local branches which do not have a upstream tracking branch
        for branch in self.gitrepo.heads:
            remote_branch = branch.tracking_branch()
            if not remote_branch:
                print('Push new local branch \'{0}\' to repo.'.format(str(branch)))
                # use git directly, second argument is refspec
                output = git.push(self.remote_gitrepo, '{}:{}'.format(str(branch), str(branch)), porcelain=True)
                # alternatively
                # push_info = self.remote_gitrepo.push(refspec='{}:{}'.format(str(branch), str(branch)))
                # get the newly created remote branch
                remote_branch = getattr(self.remote_gitrepo.refs, str(branch))
                branch.set_tracking_branch(remote_branch)
                # remove last line
                output = output[:output.rfind('\n')]
                print(output)
        # Finally push all branches with one command
        try:
            if self.force:
                output = git.push(self.remote_gitrepo, porcelain=True, force=True, all=True)
            else:
                output = git.push(self.remote_gitrepo, porcelain=True, all=True)
            print(output)
        except Exception as err:
            print(err)
        print('')

    def git_fetch(self, prune=False):

        try:
            if prune:
                fetch_iter = self.remote_gitrepo.fetch(prune=True)
            else:
                fetch_iter = self.remote_gitrepo.fetch()
        except Exception as err:
            print('Could not fetch from remote repo.')
            return 1
        for fetch_info in fetch_iter:
            print("Updated %s to %s" % (fetch_info.ref, fetch_info.commit))
        return 0

    def change_to_local_repo(self):
        # first check if the local repo exists and is a git working space
        repo_exists = os.path.isdir(self.local_path)
        print('Change to Git project \'{0}\'.'.format(self.local_path_short))
        if os.path.isdir(self.local_path + '/.git'):
            ret_val = change_dir(self.local_path)
            if ret_val != 0:
                print('Cannot change to repository \'{0}\'.'.format(self.local_path))
            return ret_val
        elif repo_exists:
            print('The repository \'{0}\' exists, but is not a git repository'.format(self.local_path))
            return 1
        else:
            # local repo does not exist and must be cloned
            parent_dir = os.path.dirname(self.local_path)
            ret_code = 0
            if not os.path.isdir(parent_dir):
                make_dir = ['mkdir', '-p', parent_dir]
                ret_code, error = run(make_dir, False)
            if ret_code == 0:
                ret_code = change_dir(parent_dir)
            else:
                return ret_code
            if ret_code != 0:
                print('Could change to \'{0}\''.format(parent_dir))
                return ret_code
            # clone git repo
            repo = Repo.clone_from(self.remote_path, self.local_path, branch='master')
            print('Clone to remote repo \'{0}\' to \'{1}\'.'.format(self.remote_reponame, self.local_path))
            if not repo:
                print('Remote repo could not be clone because of an error:\n')
                return 1
        return 0

    def get_branch_name_and_repo_from_remote_path(self, remote_branch):
        remote_branch = remote_branch.strip()
        parts = remote_branch.split('/')
        return '/'.join(parts[1:]), parts[0]
