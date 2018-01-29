import re, os

from ..util.system import run, change_dir, sanitize_path

from . import ACTION_PULL, ACTION_PUSH


class GitClientSync:
    def __init__(self, action):
        self.action = action

    def set_config(self, config, force):
        self.source_path_short = config.get('source', None)
        self.source_path = sanitize_path(self.source_path_short)
        self.target_repo = config.get('remote_repo', None)
        self.target_path = config.get('url', None)
        self.settings = config.get('settings', None)
        self.force = force

    def apply(self):
        if (self.action == ACTION_PULL):
            self.sync_pull()
        elif (self.action == ACTION_PUSH):
            self.sync_push()

    def sync_pull(self):
        return None

    def sync_push(self):
        return None
