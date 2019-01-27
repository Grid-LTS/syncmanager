import os
import re
from ..util import system
import syncmanager.util.globalproperties as globalproperties


class UnisonClientSync:

    def __init__(self, action):
        self.action = action

    def set_config(self, config, force):
        self.local_path = system.sanitize_path(config.get('source', None))
        self.settings = self.parse_settings(config.get('settings', None))
        self.force = force

    def apply(self):
        unison_dir=os.path.join(os.environ['HOME'], '.unison')
        if not os.path.exists(unison_dir):
            os.makedirs(unison_dir)
        self.load_template_file(self.settings['template'])
        
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

    def load_template_file(self,filename):
        template_dir = os.path.join(globalproperties.conf_dir, 'unison-templates')
        template_file = os.path.join(template_dir, filename)
        if os.path.exists(template_file):
            print(open(template_file).read())
            return
        else:
            template_dir = os.path.join(os.path.join(globalproperties.properties_path_prefix, 'templates'),'unison')
            #load one of built in templates
            template_file = os.path.join(template_dir, filename)
            if os.path.exists(template_file):
                print(open(template_file).read())
                return
        print("Unison template {} does not exist. Skip sync.".format(filename))
