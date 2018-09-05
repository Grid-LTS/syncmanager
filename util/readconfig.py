import re

def config_parse(path):
    """
    parse a config file and yields the config
    :param path: str
    :return: dict
    """
    conffile = open(path, 'r')
    config = {}
    mode = None
    for line in conffile:
        line = line.strip()
        source, url, rest = parse_line(line)
        # ignore empty line or comment
        if source == '' or source[0] == '#':
            continue
        if not source:
            raise StopIteration
        if url == '':
            if source.startswith("env="):
                continue
            if source == '[git]':  # The equivalent if statement
                mode = 'git'
            elif source == '[unison]':
                mode = 'unison'
            else:
                print('The sync client ' + source + ' is not supported.')
                raise StopIteration
            continue
        config['source'] = source
        if mode == 'git':
            #split url in remote repo descriptor and url
            config['remote_repo'], config['url'] = parse_remote_repo_descriptor(url)
        else:
            config['url'] = url
        config['settings'] = rest
        if not mode:
            print('No client specified in the config file \''+path+'\'. File is ignored')
            raise StopIteration
        else:
            yield mode, config

def environment_parse(path):
    conffile = open(path, 'r')
    for line in conffile:
        line = line.strip()
        source, url, rest = parse_line(line)
        if source == '' or source[0] == '#':
            continue
        if url == '':
            if not source.startswith("env="):
                return []
            # check if env parameter is given
            if len(source) > 4:
                sync_envs = source[4:].split(',')
                if not sync_envs:
                    sync_envs = source[4:].split(', ')
                return sync_envs
            else:
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

def parse_remote_repo_descriptor(url):
    parts = re.split('\|', url, maxsplit=1)
    if len(parts) == 1:
        repo_name = 'origin'
        repo_url = url
    else:
        repo_name = parts[0].strip()
        repo_url = parts[1]
    return repo_name, repo_url


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
