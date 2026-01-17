import os
import configparser
import getpass
from jinja2 import Environment, FileSystemLoader
import socket
import sys

deploy_dir = os.path.dirname(os.path.abspath(__file__))
module_root = os.path.dirname(deploy_dir)

properties_path = module_root + "/application.prod.cfg"
config = configparser.ConfigParser()
TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(os.path.join(deploy_dir, 'templates')),
    trim_blocks=False)

if os.path.isfile(properties_path):
    with open(properties_path, 'r') as propertiesfile:
        config_string = '[default_section]\n' + propertiesfile.read()
        config.read_string(config_string)
        if sys.argv[1] == 'syncmanagerapi.service':
            systemd_service_file = sys.argv[1]
            install_dir = config['default_section'].get('INSTALL_DIR', '/opt/syncmanagerapi').strip('"\'')
            fs_root_dir = config['default_section'].get('FS_ROOT', '/var/syncmanager').strip('"\'')
            context = {
                'unix_user': config['default_section'].get('UNIX_USER', 'syncman').strip('"\''),
                'unix_group': config['default_section'].get('UNIX_USER', 'syncman').strip('"\''),
                'install_dir': install_dir,
                'server_port': config['default_section'].get('SERVER_PORT', '5010'),
                'hostname': config['default_section'].get('HOSTNAME', socket.gethostname()).strip('"\'')
            }
            conf_file = TEMPLATE_ENVIRONMENT.get_template('{}.j2'.format(systemd_service_file)).render(context)
            f = open(os.path.join(deploy_dir, systemd_service_file), 'w')
            f.write(conf_file)
            f.close()

        # generate database init script
        if sys.argv[1] == 'init_db.sql':
            init_db_file = sys.argv[1]
            db_user_name = config['default_section'].get('DB_USER', 'syncmanager').strip('"\'')
            # password must be provided, in future this should be replaced by a retrieval from a password vault
            passw = getpass.getpass("Provide password for Mysql user {}:".format(db_user_name))
            if passw.isupper():
                print("All letters in password are uppercase!")
            context = {
                'db_schema_name': config['default_section'].get('DB_SCHEMA_NAME', 'syncmanerapi').strip('"\''),
                'db_user': db_user_name,
                'db_user_password': passw,
                'db_host': config['default_section'].get('DB_HOST', 'localhost').strip('"\''),
                'db_port': config['default_section'].get('DB_PORT', '3306').strip('"\''),
            }
            context[
                'database_url'] = (f"mysql://{context['db_user']}:{context['db_user_password']}"
                                   f"@{context['db_host']}:{context['db_port']}/{context['db_schema_name']}")

            conf_file = TEMPLATE_ENVIRONMENT.get_template('{}.j2'.format(init_db_file)).render(context)
            f = open(os.path.join(deploy_dir, init_db_file), 'w')
            f.write(conf_file)
            f.close()
            print(f"DB_PASSWORD=\"{passw}\"")
            alembic_conf_file = TEMPLATE_ENVIRONMENT.get_template('alembic.ini.j2'.format(init_db_file)).render(
                context)
            f_alembic = open(os.path.join(deploy_dir, "alembic.ini"), 'w')
            f_alembic.write(alembic_conf_file)
            f_alembic.close()
