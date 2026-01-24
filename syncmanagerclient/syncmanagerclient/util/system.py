import subprocess
import os

from pathlib import Path

home_dir = os.path.expanduser('~')
def execute(command, env={}, *args, **kwargs):

    # shell=True for execution in Windows
    import sys
    # its win32,
    is_windows = sys.platform.startswith('win')
    if is_windows:
        creationflags = subprocess.CREATE_NO_WINDOW
    else:
        creationflags = 0
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                               creationflags=creationflags,
                               env=env, shell=is_windows, *args, **kwargs)
    for stdout_line in iter(process.stdout.readline, ""):
        yield stdout_line
    process.stdout.close()
    # process_output, process_errors = process.communicate()
    # communicate returns bytes, so we have to decode them and remove the trailing whitespace
    exitcode = process.wait()
    if exitcode:
        raise subprocess.CalledProcessError(exitcode, command)


def run_command(command, *args, **kwargs):
    """
    Run a shell command with Popen, args & kwargs will be passed
    :param command: list[str]
    :return: int exitcode
    """
    try:
        for line in execute(command, *args, **kwargs):
            print(line, end="")
    except subprocess.CalledProcessError as e:
        print(f"Scraping failed {e.stderr}")


def change_dir(path):
    if os.path.isdir(path):
        os.chdir(path)
        return 0
    else:
        return 1


def sanitize_path(path:str, fs_root_dir = home_dir) -> Path:
    """
    makes it a valid posix path
    :param fs_root_dir: root directory of the file system
    :param path:
    :return:
    """
    if isinstance(path, Path):
        return path
    if path.startswith("~"):
        sanitized = Path(fs_root_dir).joinpath(*Path(path).parts[1:])
    else:
        sanitized = Path(path)
    return sanitized
