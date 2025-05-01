

class SyncAllConfig:

    def __init__(self, username=None, email=None,
                 settings=None):
        self.username = username
        self.email = email
        self.settings = settings

class SyncConfig(SyncAllConfig):

    def __init__(self, local_path=None, remote_repo=None, remote_repo_url=None, username=None, email=None,
                 settings=None):
        super().__init__(username=username, email=email,
                                settings=settings)
        self.remote_repo = remote_repo
        self.remote_repo_url = remote_repo_url
        self.local_path = local_path

    @classmethod
    def init(cls, local_path=None, remote_repo=None, remote_repo_url=None, allconfig : SyncAllConfig = None):
       return cls(local_path=local_path, remote_repo=remote_repo, remote_repo_url=remote_repo_url, username=allconfig.username, email=allconfig.email,
                  settings=allconfig.settings)
