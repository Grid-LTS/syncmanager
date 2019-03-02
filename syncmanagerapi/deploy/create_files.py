import os
import configparser
import getpass
from jinja2 import Environment, FileSystemLoader
import socket
import sys

deploy_dir = os.path.dirname(os.path.abspath(__file__))
module_root = os.path.dirname(deploy_dir)

properties_path = module_root + "/application.properties"
config = configparser.ConfigParser()
TEMPLATE_ENVIRONMENT = Environment(
            autoescape=False,
            loader=FileSystemLoader(os.path.join(deploy_dir,'templates')),
            trim_blocks=False)

if os.path.isfile(properties_path):
    with open(properties_path, 'r') as propertiesfile:
        config_string = '[default_section]\n' + propertiesfile.read()
        config.read_string(config_string)
        if sys.argv[1] == 'syncmanagerapi.service':
            systemd_service_file = sys.argv[1]
            context = {
                'unix_user': config['default_section'].get('unix_user','syncman'),
                'unix_group': config['default_section'].get('unix_user','syncman'),
                'install_dir' : config['default_section'].get('install_dir','/opt/syncmanagerapi'),
                'server_port' : config['default_section'].get('server_port','5010'),
                'hostname': config['default_section'].get('hostname', socket.gethostname())
            }
            conf_file = TEMPLATE_ENVIRONMENT.get_template('{}.j2'.format(systemd_service_file)).render(context)
            f = open(os.path.join(deploy_dir, systemd_service_file), 'w')
            f.write(conf_file)
            f.close()

        # generate database init script
        if sys.argv[1] == 'init_db.sql':
            init_db_file = sys.argv[1]
            db_user_name = config['default_section'].get('db_user','syncmanager')
            # password must be provided, in future this should be replaced by a retrieval from a password vault
            passw = getpass.getpass("Provide password for Mysql user {}:".format(db_user_name))
            context = {
                'db_schema_name' : config['default_section'].get('db_schema_name','syncmanerapi'),
                'db_user' :  db_user_name,
                'db_password' : passw
            }

            conf_file = TEMPLATE_ENVIRONMENT.get_template('{}.j2'.format(init_db_file)).render(context)
            f = open(os.path.join(deploy_dir, init_db_file), 'w')
            f.write(conf_file)
            f.close()
            print("db_password={}".format(passw))

