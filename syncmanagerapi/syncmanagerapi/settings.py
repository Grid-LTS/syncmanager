import os
import sys

import configparser

top_package_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(top_package_dir)
properties_dir = os.environ.get('SYNCMANAGER_SERVER_CONF', project_dir)


def import_entry_point(function_name):
    try:
        import syncmanagerapi
    except ImportError:
        sys.path.append(project_dir)
        import syncmanagerapi
    return getattr(syncmanagerapi, function_name)


def read_properties_file(environment):
    # first determine environment
    if environment == 'production':
        properties_path = os.path.join(properties_dir, 'application.properties')
    else:
        mappers = {
            'production': 'prod',
            'development': 'dev'
        }
        # in local DEV setup
        properties_path = os.path.join(properties_dir, f"application.{mappers[environment]}.properties")
    with open(properties_path) as propertiesfile:
        config = configparser.ConfigParser()
        config.optionxform = str
        config_string = '[default_section]\n' + propertiesfile.read()
        config.read_string(config_string)
        return {**config['default_section']}
