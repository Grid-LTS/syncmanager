from pathlib import Path

from ..util.globalproperties import Globalproperties

ACTION_SET_REMOTE = 'set_remote'
ACTION_SET_REMOTE_ALIASES = [ACTION_SET_REMOTE, 'set-remote']
ACTION_ADD_ENV_ALIASES = ['add_env', 'add-env']
ACTION_PUSH = 'push'
ACTION_PULL = 'pull'
ACTION_DELETE = 'delete'
ACTION_DELETE_REPO = 'delete-repo'
ACTION_SET_CONF = 'set_conf'
ACTION_SET_CONF_ALIASES = ['set_conf', 'set-conf', 'set-config', 'set_config']
ACTION_ARCHIVE_IGNORED_FILES = 'archive-ignored-files'


def get_remote_url(remote_repo_path):
    path = Path(remote_repo_path)
    if Globalproperties.ssh_user and Globalproperties.ssh_host:
        return f"ssh://{Globalproperties.ssh_user}@{Globalproperties.ssh_host}:{path.as_posix()}"
    return f"file://{path.as_posix()}"
