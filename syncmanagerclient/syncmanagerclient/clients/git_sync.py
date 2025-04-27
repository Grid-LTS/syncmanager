import os

from git import Repo, GitCommandError

from ..util.system import change_dir, sanitize_path
from .deletion_registration import DeletionRegistration
from .error import GitSyncError, GitErrorItem
from .git_base import GitClientBase

from . import ACTION_PULL, ACTION_PUSH, ACTION_DELETE

PRINCIPAL_BRANCH_MAIN = 'main'
PRINCIPAL_BRANCH_MASTER = 'master'


class GitClientSync(GitClientBase):
    def __init__(self, action):
        self.action = action
        self.errors = []

    def set_config(self, config, force):
        self.local_path_short = config.get('source', None)
        self.local_path = sanitize_path(self.local_path_short)
        self.local_reponame = os.path.basename(self.local_path)
        self.remote_reponame = config.get('remote_repo', None)
        self.remote_path = config.get('url', None)
        self.settings = config.get('settings', None)
        self.principal_branch = None
        self.force = force

    def apply(self, **kwargs):
        start_dir = os.getcwd()
        code = self.change_to_local_repo()
        if code != 0:
            return
        self.gitrepo = Repo(self.local_path)
        remotes = [remote.name for remote in self.gitrepo.remotes]
        if not self.remote_reponame in remotes:
            self.errors.append(
                GitErrorItem(self.local_path_short, f"Remote repo {self.remote_reponame} is not defined. "
                                                    f"Run 'set-remote' on this repo.", None)
            )
            return
        self.remote_gitrepo = self.gitrepo.remote(self.remote_reponame)

        self.consistency_check()

        is_initial_fetch = False
        if len(self.gitrepo.heads) == 0:
            # this can be the case if the local repo was cloned from an empty remote repo
            # pull in remote repo first
            print("No local branches. initial fetch of remote branches.")
            is_initial_fetch = True
            self.git_fetch(True)
        # checkout principal branch, this simply tests if the local workspace is in a good state
        if PRINCIPAL_BRANCH_MAIN in self.gitrepo.heads:
            try:
                self.gitrepo.git.checkout(PRINCIPAL_BRANCH_MAIN)
                self.principal_branch = PRINCIPAL_BRANCH_MAIN
                is_initial_fetch = False
            except GitCommandError as e:
                print(f"Cannot determine default branch. error={e}")
                exit(1)
        elif PRINCIPAL_BRANCH_MASTER in self.gitrepo.heads:
            try:
                self.gitrepo.git.checkout(PRINCIPAL_BRANCH_MASTER)
                self.principal_branch = PRINCIPAL_BRANCH_MASTER
                is_initial_fetch = False
            except GitCommandError as e:
                print(f"Cannot determine default branch. error={e}")
                exit(1)
        if is_initial_fetch or self.principal_branch is None:
            # initial fetch we determine the default branch from the remote repo
            try:
                default_branch = self.gitrepo.git.rev_parse("--abbrev-ref", "origin/HEAD")
                self.principal_branch = os.path.basename(default_branch)
            except GitCommandError as e:
                print(f"Cannot determine default branch. error={e}")
                remote_refs = [os.path.basename(x.path) for x in self.remote_gitrepo.refs]
                if PRINCIPAL_BRANCH_MAIN in remote_refs:
                    try:
                        self.gitrepo.git.checkout(PRINCIPAL_BRANCH_MAIN)
                        self.principal_branch = PRINCIPAL_BRANCH_MAIN
                    except GitCommandError as e:
                        print(f"Cannot determine default branch. error={e}")
                        exit(1)
                elif PRINCIPAL_BRANCH_MASTER in remote_refs:
                    try:
                        self.gitrepo.git.checkout(PRINCIPAL_BRANCH_MASTER)
                        self.principal_branch = PRINCIPAL_BRANCH_MASTER
                    except GitCommandError as e:
                        print(f"Cannot determine default branch. error={e}")
                        exit(1)
        if self.principal_branch:
            if self.gitrepo.active_branch.name != self.principal_branch:
                try:
                    getattr(self.gitrepo.heads, self.principal_branch).checkout()
                except GitCommandError as err:
                    self.errors.append(
                        GitErrorItem(self.local_path_short, err, self.principal_branch)
                    )
                    print(f"ERROR. Cannot checkout principal branch {self.principal_branch}: {str(err)}")
                    self.initial_pull()
                    return

            try:
                has_remote_branch = getattr(self.remote_gitrepo.refs, str(self.principal_branch))
            except AttributeError:
                has_remote_branch = False
            if self.action == ACTION_PUSH and has_remote_branch:
                self.gitrepo.git.remote("set-head", self.remote_reponame, self.principal_branch)
            self.initial_pull()

        if self.action == ACTION_PULL or self.action == ACTION_PUSH:
            # PULL and PUSH are the only actions that happen online, where an actual sync with the remote repo happens
            # fetch and prune all branches in local repo
            self.git_fetch(True)
            self.sync_deletion()
            # delete local branches with with the remote tracking branches 'gone',
            self.cleanup_orphaned_local_branches()
            self.sync_push()
            # nothing to do for ACTION_PULL as the updates have been sync with FETCH
        elif self.action == ACTION_DELETE:
            self.delete_local_branch(**kwargs)
        change_dir(os.path.dirname(start_dir))
        self.close()

    def initial_pull(self):
        git = self.gitrepo.git
        try:
            remote_branch = getattr(self.remote_gitrepo.refs, str(self.gitrepo.active_branch.name))
        except AttributeError:
            print("Cannot sync since there is no remote branch")
            return
        self.gitrepo.active_branch.set_tracking_branch(remote_branch)
        try:
            out = git.pull(self.remote_reponame, with_stdout=True, ff_only=True)
        except GitCommandError as err:
            self.errors.append(
                GitErrorItem(self.local_path_short, err, self.principal_branch)
            )
            print(f"ERROR. Cannot pull {self.principal_branch}: {str(err)}")
            return
        print(out)

    def delete_local_branch(self, **kwargs):
        path = kwargs.get('path', None)
        if not path:
            print('Error. No branch given.')
            exit(1)
        print('Deleting branch {}.'.format(path))
        try:
            out = self.gitrepo.delete_head(path, force=True)
        except GitCommandError as e:
            print(f"Local branch cannot be deleted: {e}")
            return
        if out:
            print(out)

    def sync_deletion(self):
        # deleted local branches will be removed on the remote
        git = self.gitrepo.git
        deletion_registry = DeletionRegistration(mode='git')
        entries = deletion_registry.read_and_flush_registry(self.remote_reponame)
        entries_copy = entries[:]
        for index, entry in enumerate(entries_copy):
            if not self.local_path == sanitize_path(entry[0]):
                continue
            branch_path = entry[1]
            branch_path_full = self.remote_reponame + '/' + branch_path
            remote_branches = [r.name for r in self.remote_gitrepo.refs]
            if branch_path_full in remote_branches:
                print('Branch {} is deleted in remote repository {}'.format(branch_path_full, self.remote_reponame))
                if branch_path == PRINCIPAL_BRANCH_MAIN:
                    print(f"Branch {PRINCIPAL_BRANCH_MAIN} cannot be deleted")
                    continue
                if branch_path == PRINCIPAL_BRANCH_MASTER:
                    main_branch = getattr(self.gitrepo.heads, PRINCIPAL_BRANCH_MAIN)
                    if not main_branch:
                        # create main branch
                        self.gitrepo.git.checkout('-b', PRINCIPAL_BRANCH_MAIN)
                        self.principal_branch = PRINCIPAL_BRANCH_MAIN
                        git.push(self.remote_gitrepo, '{}:{}'.format(PRINCIPAL_BRANCH_MAIN, PRINCIPAL_BRANCH_MAIN),
                                 porcelain=True)
                    self.gitrepo.git.remote('set-head', self.remote_reponame, self.principal_branch)
                try:
                    git.push(self.remote_gitrepo, '--delete', str(branch_path), porcelain=True)
                except GitCommandError:
                    print(f"Cannot delete {branch_path} on remote. Is it set as default in remote repo?")
            else:
                print('Branch {} was already removed in remote repository {}'.format(branch_path_full,
                                                                                     self.remote_reponame))
            if hasattr(self.gitrepo.heads, str(branch_path)):
                # Delete local working branch if still existing
                out = self.gitrepo.delete_head(branch_path)
                print(out)
            entries.remove(entry)
        if len(entries) > 0:
            deletion_registry.write_registry(self.remote_reponame, entries)

    def cleanup_orphaned_local_branches(self):
        # get all branches that have a remote tracking branch, that is not part of the remote refs anymore
        for branch in self.gitrepo.heads:
            # do not delete principal branch
            if str(branch) == self.principal_branch or str(branch) == 'HEAD':
                continue
            remote_tracking = branch.tracking_branch()
            parts = str(remote_tracking).split('/')
            remote_repo = parts[0]
            # skip if the tracking branch belongs to another remote repo
            if remote_repo != str(self.remote_gitrepo):
                continue
            if remote_tracking and not remote_tracking in self.remote_gitrepo.refs:
                print('Delete orphaned branch \'{0}\''.format(branch))
                self.gitrepo.delete_head(branch, "-D")

    def sync_push(self):
        git = self.gitrepo.git
        # find all local branches which do not have a upstream tracking branch
        for branch in self.gitrepo.heads:
            remote_branch = branch.tracking_branch()
            # check that the remote branch is in refs
            if not remote_branch or not remote_branch in self.remote_gitrepo.refs:
                print('Push new local branch \'{0}\' to repo.'.format(str(branch)))
                # use git directly, second argument is refspec
                output = git.push("--set-upstream", self.remote_gitrepo, str(branch), porcelain=True)
                # alternatively
                # push_info = self.remote_gitrepo.push(refspec='{}:{}'.format(str(branch), str(branch)))
                # get the newly created remote branch
                if hasattr(self.remote_gitrepo.refs, str(branch)):
                    remote_branch = getattr(self.remote_gitrepo.refs, str(branch))
                    branch.set_tracking_branch(remote_branch)
                # remove last line
                output = output[:output.rfind('\n')]
                print(output)
            else:
                print(branch)
                try:
                    branch.checkout()
                except GitCommandError as err:
                    self.errors.append(
                        GitErrorItem(self.local_path_short, err, str(branch))
                    )
                    print(str(err))
                    continue
                # this branch tracks an upstream branch, we need to ensure that the remote branch and 
                # the working branch are merged
                if self.action == ACTION_PULL and self.force:
                    # force pull of the remote repo
                    git.reset('--hard', str(remote_branch))
                    print('Force reset of local branch \'{0}\' to remote ref.'.format(str(branch)))
                    continue
                # first merge with upstream branches
                # this will only merge if no conflicts present
                # Todo: first check if the upstream has changes, e.g. a differing commit 
                try:
                    self.remote_gitrepo.pull(rebase=True)
                except GitCommandError as err:
                    unstaged_uncommitted = ["unstaged changes", "uncommitted changes"]
                    has_diff = False
                    for mes in unstaged_uncommitted:
                        if mes in err.stderr:
                            has_diff = True

                    if has_diff:
                        self.errors.append(
                            GitErrorItem(self.local_path_short, err, str(branch))
                        )
                        print(str(err))
                    else:
                        # merge conflict needs to be resolved manually
                        git.rebase('--abort')
                        self.errors.append(
                            GitErrorItem(self.local_path_short, err, str(branch))
                        )
                        print(str(err))
                        continue
                except Exception as err:
                    self.errors.append(
                        GitErrorItem(self.local_path_short, err, str(branch))
                    )
                    continue

                # Finally push the branch
                # Todo: check possibility of --force-with-lease
                try:
                    if self.force:
                        output = git.push(self.remote_gitrepo, porcelain=True, force=True)
                    else:
                        output = git.push(self.remote_gitrepo, porcelain=True)
                    print(output)
                except Exception as err:
                    self.errors.append(
                        GitErrorItem(self.local_path_short, err, f"git push fails for {str(branch)}")
                    )
        # finally checkout principal branch
        if len(self.gitrepo.heads) > 0 and self.principal_branch:
            try:
                getattr(self.gitrepo.heads, self.principal_branch).checkout()
            except GitCommandError as err:
                self.errors.append(
                    GitErrorItem(self.local_path_short, err, self.principal_branch)
                )
                print(f"ERROR. Cannot checkout principal branch {self.principal_branch}: {str(err)}")
                return
        else:
            message = 'No principal branch available. Did you make an initial commit?'
            error = GitSyncError(message)

            self.errors.append(
                GitErrorItem(self.local_path_short, error, 'master or main')
            )
            print(message)
        print('')

    def git_pull(self, git, branch):
        try:
            # just pull all updates
            out = git.pull(None, with_stdout=True)
            print(out)
        except GitCommandError as err:
            self.errors.append(
                GitErrorItem(self.local_path_short, err, str(branch))
            )
            print(f"ERROR: {str(err)}")

    def git_fetch(self, prune=False):

        try:
            if prune:
                fetch_iter = self.remote_gitrepo.fetch(prune=True)
            else:
                fetch_iter = self.remote_gitrepo.fetch()
        except Exception as err:
            message = 'Could not fetch from remote repo.'
            self.errors.append(
                GitErrorItem(self.local_path_short, err, message)
            )
            print(message)
            return 1
        for fetch_info in fetch_iter:
            print("Updated %s to %s" % (fetch_info.ref, fetch_info.commit))
        return 0

    def change_to_local_repo(self):
        # first check if the local repo exists and is a git working space
        repo_exists = os.path.isdir(self.local_path)
        print('Change to Git project \'{0}\'.'.format(self.local_path_short))
        if os.path.isdir(os.path.join(self.local_path, '.git')):
            ret_val = change_dir(self.local_path)
            if ret_val != 0:
                print('Cannot change to repository \'{0}\'.'.format(self.local_path))
            return ret_val
        elif repo_exists:
            message = f"The repository '{self.local_path}' exists, but is not a git repository"
            error = GitSyncError(message)
            self.errors.append(
                GitErrorItem(self.local_path_short, error, "git clone")
            )
            print(message)
            return 1
        else:
            # local repo does not exist and must be cloned
            parent_dir = os.path.dirname(self.local_path)
            ret_code = 0
            if not os.path.isdir(parent_dir):
                os.makedirs(parent_dir)
                ret_code = change_dir(parent_dir)
            if ret_code != 0:
                print('Could change to \'{0}\''.format(parent_dir))
                return ret_code
            # clone git repo
            try:
                repo = Repo.clone_from(self.remote_path, self.local_path)
                print('Clone to remote repo \'{0}\' to \'{1}\'.'.format(self.remote_reponame, self.local_path))
            except GitCommandError as err:
                repo = None
                self.errors.append(
                    GitErrorItem(self.local_path_short, err, 'git clone')
                )
                print(f"ERROR: {str(err)}")
            if not repo:
                print('Remote repo could not be clone because of an error:\n')
                return 1
        return 0

    def consistency_check(self):
        url = next(self.remote_gitrepo.urls)
        if url != self.remote_path:
            print(f"The Git url of remote repo '{self.remote_reponame}' differs from the server url.")
            print(f"The Git url: {url}")
            print(f"Server url: {self.remote_path}")
            self.remote_gitrepo.set_url(self.remote_path)
