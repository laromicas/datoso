"""Command executor

This module provides a wrapper for subprocess.Popen to execute commands.
"""
import logging
from subprocess import PIPE, CalledProcessError, Popen


class Command:
    """Subprocess wrapper"""

    def __init__(self, command):
        self.command = command

    @staticmethod
    def execute(args, cwd=None, env=None, universal_newlines=True, shell=False):
        """Execute a command, allows to write to log and stdout."""
        # pylint: disable=consider-using-with
        def execute(args):
            popen = Popen(args, stdout=PIPE, universal_newlines=universal_newlines, cwd=cwd, env=env, shell=shell)
            yield from iter(popen.stdout.readline, '')
            popen.stdout.close()
            return_code = popen.wait()
            if return_code:
                raise CalledProcessError(return_code, args)

        for output in execute(args):
            logging.info(output)
