""" Command executor

This module provides a wrapper for subprocess.Popen to execute commands.
"""
import logging
from subprocess import PIPE, CalledProcessError, Popen
from datoso.configuration import config

class Command:
    """ Subprocess wrapper """
    quiet = config.getboolean('COMMAND', 'Quiet', fallback=False)
    verbose = config.getboolean('COMMAND', 'Verbose', fallback=False)
    logging = config.getboolean('LOG', 'Logging', fallback=False)
    logfile = config.get('LOG', 'LogFile', fallback='datoso.log')

    def __init__(self, command):
        self.command = command

    @staticmethod
    def execute(args, cwd=None, env=None, universal_newlines=True, shell=False):
        """ Execute a command, allows to write to log and stdout. """
        # pylint: disable=consider-using-with
        def execute(args):
            popen = Popen(args, stdout=PIPE, universal_newlines=universal_newlines, cwd=cwd, env=env, shell=shell)
            for stdout_line in iter(popen.stdout.readline, ""):
                yield stdout_line
            popen.stdout.close()
            return_code = popen.wait()
            if return_code:
                raise CalledProcessError(return_code, args)

        for output in execute(args):
            logging.info(output)
