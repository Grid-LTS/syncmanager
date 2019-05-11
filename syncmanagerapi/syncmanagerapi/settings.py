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
    with open(os.path.join(project_dir, 'application.properties')) as propertiesfile:
        config = configparser.ConfigParser()
        config.optionxform = str
        config_string = '[default_section]\n' + propertiesfile.read()
        config.read_string(config_string)
        # read installation dependent properties
        instance_properties_path = config['default_section'].get('INSTALL_DIR')
        instance_propertiesfile = open(os.path.join(instance_properties_path,'conf/vars.conf'), 'r')
        instanceconfig = configparser.ConfigParser()
        instanceconfig.optionxform = str
        config_string = '[default_section]\n' + instance_propertiesfile.read()
        instanceconfig.read_string(config_string)
        return {**config['default_section'], **instanceconfig['default_section'] }
