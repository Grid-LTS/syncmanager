

class GitSyncError(Exception):
    pass


class GitErrorItem:

    def __init__(self, local_repo_path, error, context=None):
        self.local_repo_path = local_repo_path
        self.error = error
        self.context = context
