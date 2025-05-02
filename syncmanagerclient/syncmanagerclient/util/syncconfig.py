

class SyncAllConfig:
    """
    SyncAllConfig is the static config defined by the ini file
    """

    def __init__(self, username=None, email=None,
                 settings=None, retention_years=None):
        self.username = username
        self.email = email
        self.settings = settings
        self.retention_years = retention_years

class SyncConfig(SyncAllConfig):
    """
    SyncConfig derives from and shares with SyncAllConfig because some of the static config in SyncAllConfig should be
    overwritten and configured dynamically via command line parameter
    """

    def __init__(self, local_path=None, remote_repo=None, remote_repo_url=None, username=None, email=None,
                 settings=None, retention_years=None):
        super().__init__(username=username, email=email,
                                settings=settings, retention_years=retention_years)
        self.remote_repo = remote_repo
        self.remote_repo_url = remote_repo_url
        self.local_path = local_path

    @classmethod
    def init(cls, local_path=None, remote_repo=None, remote_repo_url=None, allconfig : SyncAllConfig = None):
       return cls(local_path=local_path, remote_repo=remote_repo, remote_repo_url=remote_repo_url, username=allconfig.username, email=allconfig.email,
                  settings=allconfig.settings, retention_years=allconfig.retention_years)
