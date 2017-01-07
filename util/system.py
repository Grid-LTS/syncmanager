import subprocess
import logging

logger = logging.getLogger(__name__)

def run(command, softfail=False, capture=False, *args, **kwargs):
    """
    Run a shell command. Additional args & kwargs will be passed to Popen
    :param capture: bool If true, return the stdout to the caller
    :param softfail: bool If true, do not raise a RuntimeError if command fails
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

    if process_output:
        logger.debug(process_output)

    if process_errors:
        logger.error(process_errors)

    exitcode = process.wait()
    if exitcode != 0:
        if softfail:
            logger.info('Command failed,  resuming.')
        else:
            raise RuntimeError("Command did not terminate properly. Abort. (exitcode={}): {}\nOutput: {}".format(exitcode, process_errors, process_output))

    if capture:
        return process_output
    else:
        return exitcode