import subprocess


def run(command, listen=False, *args, **kwargs):
    """
    Run a shell command with Popen, args & kwargs will be passed
    :param listen: bool If true, return the stdout
    :param command: list[str]
    :return: int exitcode
    """

    process_output = None
    exitcode = None
    # Try it at least once, hence the +1
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, *args, **kwargs)
    process_output, process_errors = process.communicate()
    # communicate returns bytes, so we have to decode them and remove the trailing whitespace
    process_output = process_output.decode('utf-8').rstrip()
    process_errors = process_errors.decode('utf-8').rstrip()
    exitcode = process.wait()
    if listen:
        return process_output
    else:
        return exitcode