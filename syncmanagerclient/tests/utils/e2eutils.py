import shutil
import stat

from git import Repo
from pathlib import Path

from .testutils import *

from syncmanagerclient.main import execute_command
from syncmanagerclient.util.system import change_dir
import syncmanagerclient.util.globalproperties as globalproperties

from testlib.testsetup import USER_CLIENT_ENV



def setup_local_repo():
    repos_dir = os.path.join(test_dir, 'repos')
    shutil.rmtree(repos_dir, ignore_errors=True, onerror=lambda func, path, _: (os.chmod(path, stat.S_IWRITE), func(path)))
    if not os.path.exists(repos_dir):
        os.mkdir(repos_dir)
    local_repo = Repo.init(local_repo_path)
    change_dir(local_repo_path)
    # create file and commit
    test_file_path = os.path.join(local_repo_path, 'file.txt')
    Path(test_file_path).touch()
    local_repo.index.add([test_file_path])
    local_repo.index.commit("Initial commit on pricipal branch")
    globalproperties.set_prefix(os.path.dirname(test_dir))
    globalproperties.read_config('e2e')
    globalproperties.test_mode = True
    execute_command('set-remote', "git", USER_CLIENT_ENV, "e2e_repo", "origin")
    return local_repo
