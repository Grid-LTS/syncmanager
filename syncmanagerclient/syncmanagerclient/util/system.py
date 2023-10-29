import subprocess
import os
import pathlib
from pathlib import PurePosixPath, Path

home_dir = os.path.expanduser('~')
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
    if isinstance(path, Path):
        return path
    posix = PurePosixPath(path)
    parts = list(posix.parts)
    if parts[0] == '~':
        parts[0] = home_dir
    ret_path = pathlib.Path(*parts)
    return ret_path


def change_dir(path):
    if os.path.isdir(path):
        os.chdir(path)
        return 0
    else:
        return 1

