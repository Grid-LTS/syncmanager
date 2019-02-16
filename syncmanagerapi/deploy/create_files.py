import os
import configparser
from jinja2 import Environment, FileSystemLoader
import socket

deploy_dir = os.path.dirname(os.path.abspath(__file__))
module_root = os.path.dirname(deploy_dir)

properties_path = module_root + "/application.properties"
config = configparser.ConfigParser()
if os.path.isfile(properties_path):
    with open(properties_path, 'r') as f:
        config_string = '[default_section]\n' + f.read()
        config.read_string(config_string)
        systemd_service_file = 'syncmanagerapi.service'
        TEMPLATE_ENVIRONMENT = Environment(
            autoescape=False,
            loader=FileSystemLoader(os.path.join(deploy_dir,'templates')),
            trim_blocks=False) 
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
