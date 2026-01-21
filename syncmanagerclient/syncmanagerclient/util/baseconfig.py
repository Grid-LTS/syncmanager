from __future__ import annotations


class GlobalConfig:
    def __init__(self, filesystem_root_dir, retention_years=None, refresh_rate_months=None, ):
        self.retention_years = retention_years
        self.refresh_rate_months = refresh_rate_months
        self.filesystem_root_dir = filesystem_root_dir


class SyncAllConfig:
    """
    SyncAllConfig is the static config given ini file and the run parameters provided on the command line
    The paramters here, different to Globalproperties, are dynamic, e.g. they can be set via command line parameters
    They can be overwritten by special config for the repos. Globalproperties cannot overwitten, they are fixed for all
    repos.
    """

    def __init__(self, args, sync_env=None, username=None, email=None, organization=None,
                 settings=None, global_config=None):
        self.args = args
        if sync_env:
            self.sync_env = sync_env
        else:
            self.sync_env = args.env
        self.username = username
        self.email = email
        self.organization = organization
        self.settings = settings
        self.global_config = global_config
        if args:
            self.offline = args.offline
            self.dry_run = args.dryrun
        else:
            self.offline = False
            self.dry_run = False