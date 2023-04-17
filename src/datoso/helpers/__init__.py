"""
Helpers
"""
import re
import os
from dateutil import parser

class Bcolors:
    # pylint: disable=anomalous-backslash-in-string
    """ Color class. """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BOLDBLUE = '\e[1;34m'
    BOLDCYAN = '\e[1;36m'
    BOLDGREEN = '\e[1;32m'
    BOLDRED = '\e[1;31m'
    BOLDYELLOW = '\e[1;33m'
    BOLDWHITE = '\e[1;37m'
    BOLDMAGENTA = '\e[1;35m'

    @staticmethod
    def color_list() -> list:
        """ Return list of colors. """
        return [attr for attr in Bcolors.__dict__ if not callable(getattr(Bcolors, attr)) and not attr.startswith("__")]

    @staticmethod
    def no_color() -> None:
        """ Disables color output. """
        for color in Bcolors.color_list():
            setattr(Bcolors, color, '')

    @staticmethod
    def remove_color(string) -> str:
        """ Remove color from string. """
        if not string:
            return ''
        for color in Bcolors.color_list():
            string = string.replace(getattr(Bcolors, color), '')
        return string

def is_date(string, fuzzy=False) -> bool:
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parser.parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False


def sizeof_fmt(num, suffix="B") -> str:
    """ Convert bytes to human readable format. """
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num: .1f}Yi{suffix}"

def is_git_path(path) -> bool:
    """ Check if a path is a git repository. """
    pattern = re.compile((r"((git|ssh|http(s)?)|(git@[\w\.]+))(:(//)?)([\w\.@\:/\-~]+)(\.git)(/)?"))
    return pattern.match(path)

def is_git_repo(path) -> bool:
    """ Check if a path is a git repository. """
    if os.path.isdir(os.path.join(path, ".git")):
        return True
    return False
