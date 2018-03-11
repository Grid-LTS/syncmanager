import subprocess, os


def run(command, listen=False, *args, **kwargs):
    """
    Run a shell command with Popen, args & kwargs will be passed
    :param listen: bool If true, return the stdout
    :param command: list[str]
    :return: int exitcode
    """
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, *args, **kwargs)
    process_output, process_errors = process.communicate()
    # communicate returns bytes, so we have to decode them and remove the trailing whitespace
    process_output = process_output.decode('utf-8').rstrip()
    process_errors = process_errors.decode('utf-8').rstrip()
    exitcode = process.wait()
    if listen:
        return process_output, process_errors
    else:
        return exitcode, process_errors


def sanitize_path(path):
    if path.startswith('~'):
        home_directory_path = os.environ.get('HOME', None)
        path = path.replace('~', home_directory_path)
    return path


def change_dir(path):
    if os.path.isdir(path):
        os.chdir(path)
        return 0
    else:
        return 1

