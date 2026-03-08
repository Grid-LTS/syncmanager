from __future__ import annotations

import re

from configparser import ConfigParser

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


class ArchiveConfig:

    def __init__(self, properties_path):
        config = ConfigParser()
        config.read(properties_path)
        self.build_and_cache = ArchiveConfig.parse_and_prune(
            config.get('config', 'build_and_cache',
                       fallback="__pycache__,.pytest_cache,.gradle,gradle,"
                                "bin,build,out,target,poetry.lock,package-lock.json,gradle-wrapper.jar"))
        self.dependency_dirs = ArchiveConfig.parse_and_prune(
            config.get('config', 'dependency_dirs', fallback='.venv,venv,dist,node_modules,vendor'))
        self.skip_directories = ArchiveConfig.parse_and_prune(
            config.get('config', 'skip_directories', fallback='lib,.temp,tmp,temp,.tmp,logs'))
        self.skip_directories += ["test", "tests", ".git"]
        self.skip_regex_pattern = [re.compile(x) for x in ArchiveConfig.parse_and_prune(
            config.get('config', 'skip_files_with_regex',
                       fallback='.*\.iml$, .*\.lock$, .*\.egg-info$, .*\.log,projectFilesBackup[0-9]?$, .*\.class,.*\.pyc'))]
        self.environment_files = ArchiveConfig.parse_and_prune(
            config.get('config', 'environment_files', fallback='.DS_Store'))
        self.code_file_extensions = ArchiveConfig.parse_and_prune(
            config.get('config', 'code_file_extensions', fallback=''))
        self.archivable_dirs = ArchiveConfig.parse_and_prune(
            config.get('config', 'archivable_dirs', fallback=''))
        self.max_archive_filesize_MB = int(config.get('config', 'max_archive_filesize_MB', fallback='10'))


    def skip_list(self):
        return self.dependency_dirs + self.environment_files

    def skip_directory_list(self):
        return self.build_and_cache + self.skip_directories

    @staticmethod
    def parse_and_prune(value):
        if not value:
            return []
        return [item.strip() for item in value.split(',')]