import re

from configparser import ConfigParser


class ArchiveConfig:

    def __init__(self, properties_path):
        config = ConfigParser()
        config.read(properties_path)
        self.build_and_cache = ArchiveConfig.parse_and_prune(
            config.get('config', 'build_and_cache',
                       fallback="__pycache__,.pytest_cache,.gradle,gradle,"
                                "build,out,target,poetry.lock,package-lock.json,gradle-wrapper.jar"))
        self.dependency_dirs = ArchiveConfig.parse_and_prune(
            config.get('config', 'dependency_dirs', fallback='.venv,venv,dist,node_modules'))
        self.skip_directories = ArchiveConfig.parse_and_prune(
            config.get('config', 'skip_directories', fallback='lib,.temp,tmp,temp,.tmp,logs'))
        self.skip_directories += ["test", "tests", ".git"]
        self.skip_regex_pattern = [re.compile(x) for x in ArchiveConfig.parse_and_prune(
            config.get('config', 'skip_files_with_regex',
                       fallback='.*\.iml$, .*\.lock$, .*\.egg-info$, access\.log'))]
        self.environment_files = ArchiveConfig.parse_and_prune(
            config.get('config', 'environment_files', fallback='.DS_Store'))
        self.code_file_extensions = ArchiveConfig.parse_and_prune(
            config.get('config', 'code_file_extensions', fallback=''))
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
