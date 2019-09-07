import os
import re
from jinja2 import Environment, FileSystemLoader
from ..util import system
import syncmanagerclient.util.globalproperties as globalproperties


class UnisonClientSync:
    unison_dir = os.path.join(os.environ['HOME'], '.unison')

    def __init__(self, action):
        self.action = action
        self.errors = []

    def set_config(self, config, force):
        self.local_path = system.sanitize_path(config.get('source', None))
        self.server_path = system.sanitize_path(config.get('source', None))
        self.settings = self.parse_settings(config.get('settings', None))
        self.force = force

    def apply(self):
        self.setup_local_dirs()
        try:
            self.load_template_file(self.settings['template'])
        except FileNotFoundError as e:
            print(e)
            return
        print('Unison syncing of {}'.format(self.local_path))

    @staticmethod
    def parse_settings(settings_string):
        settings_string = settings_string.strip()
        if not settings_string:
            return {"template": "sm_default.prf"}
        parts_space = re.split(' ', settings_string, maxsplit=1)
        parts_tab = re.split('\t', settings_string, maxsplit=1)
        if len(parts_space) > len(parts_tab):
            template = parts_space[0]
        else:
            template = parts_tab[0]
        # no other settings considered yet
        if template[-4:] != '.prf':
            template += '.prf'
        return {"template": template}

    def load_template_file(self, filename):
        template_dir = os.path.join(globalproperties.conf_dir, 'unison-templates')
        template_file = os.path.join(template_dir, filename)
        exists = False
        if os.path.exists(template_file):
            exists = True
        else:
            template_dir = os.path.join(os.path.join(globalproperties.properties_path_prefix, 'templates'), 'unison')
            # load one of built in templates
            template_file = os.path.join(template_dir, filename)
            if os.path.exists(template_file):
                exists = True
        if exists:
            TEMPLATE_ENVIRONMENT = Environment(
                autoescape=False,
                loader=FileSystemLoader(template_dir),
                trim_blocks=False)
            context = {
                'local_path': self.local_path,
                'server_path': self.server_path
            }
            unison_sync_file = TEMPLATE_ENVIRONMENT.get_template(filename).render(context)
            f = open(os.path.join(__class__.unison_dir, filename), 'w')
            f.write(unison_sync_file)
            f.close()
        else:
            raise FileNotFoundError("Unison template {} does not exist. Skip sync.".format(filename))

    def setup_local_dirs(self):
        if not os.path.exists(__class__.unison_dir):
            os.makedirs(__class__.unison_dir)
        if not os.path.exists(self.local_path):
            os.makedirs(self.local_path)
