import re, os

DEV_ENV = os.environ.get('DEV_ENV', None)


def config_parse(path):
    """
    parse a config file and yields the config
    :param path:
    :return: dict
    """
    file = open(path, 'r')

    config = {}
    for line in file:
        line = line.strip()
        source, url, rest = parse_line(line)
        if (source == '' or source[0] == '#'):
            source, url, rest = parse_next_line(file)
        if (source == False):
            raise StopIteration
        if (url == ''):
            if (source.startswith("env=") and DEV_ENV):
                # check if env parameter is given
                if len(source) > 4:
                    envs = source[4:].split(', ')
                else:
                    envs = []
                if (DEV_ENV in envs):
                    # continue to next line
                    source, url, rest = parse_next_line(file)
                else:
                    raise StopIteration
            if source == '[git]':  # The equivalent if statement
                config['mode'] = 'git'
            elif source == '[unison]':
                config['mode'] = 'unison'
            else:
                print('The sync mode ' + source + ' is not supported.')
                raise StopIteration
            source, url, rest = parse_next_line(file)
        config['source'] = source
        config['url'] = url
        config['settings'] = rest
        if (not config.get('mode', None)):
            raise StopIteration
        else:
            yield config


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


def parse_next_line(file):
    try:
        line = file.__next__()
        line = line.strip()
        while (len(line) == 0 or line[0] == '#'):
            line = file.__next__()
            line = line.strip()
        return parse_line(line)
    except (StopIteration):
        return False, False, False
