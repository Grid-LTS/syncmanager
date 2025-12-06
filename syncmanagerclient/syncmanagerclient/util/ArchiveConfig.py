from configparser import ConfigParser


class ArchiveConfig:

    def __init__(self, properties_path):
        config = ConfigParser()
        config.read(properties_path)
        self.build_and_cached_dirs = ArchiveConfig.parse_and_prune(config.get('config', 'build_and_cached_dirs', fallback=''))
        self.dependency_dirs = ArchiveConfig.parse_and_prune(config.get('config', 'dependency_dirs', fallback=''))
        self.ignore_directories = ArchiveConfig.parse_and_prune(config.get('config', 'ignore_directories', fallback=''))
        self.build_artefacts = ArchiveConfig.parse_and_prune(config.get('config', 'build_artefacts', fallback=''))
        self.optional_files = ArchiveConfig.parse_and_prune(config.get('config', 'optional_files', fallback=''))
        self.environment_files =  ArchiveConfig.parse_and_prune(config.get('config', 'environment_files', fallback=''))
        self.code_file_extensions = ArchiveConfig.parse_and_prune(config.get('config', 'code_file_extensions', fallback=''))
        self.max_archive_filesize_MB = int(config.get('config', 'max_archive_filesize_MB', fallback='10'))

    def skip_list(self):
        return self.dependency_dirs + self.environment_files + self.optional_files + self.build_artefacts

    def skip_directory_list(self):
        return  self.build_and_cached_dirs + self.ignore_directories
    
    @staticmethod
    def parse_and_prune(value):
        if not value:
            return []
        return [item.strip() for item in value.split(',')]