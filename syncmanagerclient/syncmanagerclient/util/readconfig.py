import re


class ConfigParser:
    
    def __init__(self, path):
        self.config = {}
        self.mode = None
        self.path = path

    def parse(self):
        """
        parse a config file and yields the config
        :return: dict
        """
        conffile = open(self.path, 'r') 
        for line in conffile:
            line = line.strip()
            source, url, rest = parse_line(line)
            # ignore empty line or comment
            if source == '' or source[0] == '#':
                continue
            if not source:
                conffile.close()
                raise StopIteration
            if url == '':
                if source.startswith("env="):
                    continue
                if source == '[git]':  # The equivalent if statement
                    self.mode = 'git'
                elif source == '[unison]':
                    self.mode = 'unison'
                else:
                    print('The sync client ' + source + ' is not supported.')
                    conffile.close()
                    raise StopIteration
                continue
            self.config['source'] = source
            if self.mode == 'git':
                # split url in remote repo descriptor and url
                self.parse_remote_repo_descriptor(url)
            else:
                self.config['url'] = url
            self.config['settings'] = rest
            if not self.mode:
                print(f"No client specified in the config file '{self.path}'. File is ignored")
                conffile.close()
                raise StopIteration
            else:
                yield self.mode, self.config
        conffile.close()

    def parse_remote_repo_descriptor(self, url):
        parts = re.split('\|', url, maxsplit=1)
        if len(parts) == 1:
            repo_name = 'origin'
            repo_url = url
        else:
            repo_name = parts[0].strip()
            repo_url = parts[1]
        self.config['remote_repo'] = repo_name
        self.config['url'] = repo_url

    def parse_settings(self):
        pass


def environment_parse(path):
    conffile = open(path, 'r')
    for line in conffile:
        line = line.strip()
        source, url, rest = parse_line(line)
        if source == '' or source[0] == '#':
            continue
        if url == '':
            if not source.startswith("env="):
                conffile.close()
                return []
            # check if env parameter is given
            if len(source) > 4:
                sync_envs = source[4:].split(',')
                if not sync_envs:
                    sync_envs = source[4:].split(', ')
                conffile.close()
                return sync_envs
            conffile.close()
            return []


def parse_line(line):
    parts = re.split(' |\t', line, maxsplit=2)
    source = parts[0].strip()
    if len(parts) >= 2:
        url = parts[1].strip()
    else:
        url = ''
    if len(parts) >= 3:
        rest = parts[2].strip()
    else:
        rest = ''
    return source, url, rest


def parse_next_line(conffile):
    try:
        line = conffile.__next__()
        line = line.strip()
        while len(line) == 0 or line[0] == '#':
            line = conffile.__next__()
            line = line.strip()
        return parse_line(line)
    except StopIteration:
        return False, False, False