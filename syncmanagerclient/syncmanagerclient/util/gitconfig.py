class GitConfig:

    def __init__(self, local_path=None, remote_repo=None, remote_repo_url=None, username=None, email=None,
                 settings=None):
        self.remote_repo = remote_repo
        self.remote_repo_url = remote_repo_url
        self.local_path = local_path
        self.username = username
        self.email = email
        self.settings = settings
