import os
import sys

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


def get_properties_path(environment, _properties_dir=properties_dir):
    # first determine environment
    if environment == 'production':
        properties_path = os.path.join(_properties_dir, 'application.prod.cfg')
        if os.path.isfile(properties_path):
            return properties_path
        return os.path.join(_properties_dir, 'application.prod.cfg')
    else:
        mappers = {
            'production': 'prod',
            'development': 'dev',
            'test': "test"
        }
        # in local DEV setup
    return os.path.join(_properties_dir, f"application.{mappers[environment]}.cfg")
