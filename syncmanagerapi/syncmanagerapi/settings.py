import os
import sys

import configparser

top_package_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(top_package_dir)


def import_entry_point(function_name):
    try:
        import syncmanagerapi
    except ImportError:
        sys.path.append(project_dir)
        import syncmanagerapi
    return getattr(syncmanagerapi, function_name)


def read_properties_file():
    # first determine environment
    if os.environ.get('SYNCMANAGER_SERVER_CONF', None):
        properties_dir = os.environ['SYNCMANAGER_SERVER_CONF']
    else:
        # DEV environment
        install_properties_path = os.path.join(project_dir, 'application.properties')
        install_propertiesfile = open(install_properties_path, 'r')
        install_config = configparser.ConfigParser()
        install_config.optionxform = str
        config_string = '[default_section]\n' + install_propertiesfile.read()
        install_config.read_string(config_string)
        properties_dir = os.path.join(install_config['default_section'].get('INSTALL_DIR'), 'conf')
    properties_path = os.path.join(properties_dir, 'application.properties')
    with open(properties_path) as propertiesfile:
        config = configparser.ConfigParser()
        config.optionxform = str
        config_string = '[default_section]\n' + propertiesfile.read()
        config.read_string(config_string)
        return {**config['default_section']}
