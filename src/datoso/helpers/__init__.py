"""
Helpers
"""
__all__ = ['downloader']
from contextlib import suppress
from enum import Enum
import re
import os
from pathlib import Path

from dateutil import parser
import shutil

from datoso.helpers.download import downloader

class Bcolors:
    # pylint: disable=anomalous-backslash-in-string
    """ Color class. """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ERROR = '\033[91m'
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
    if Path.is_dir(Path(path, ".git")):
        return True
    return False

class FileUtils:

    @staticmethod
    def copy(origin, destination):
        """ Copy file to destination. """
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        try:
            if os.path.isdir(origin):
                with suppress(FileNotFoundError):
                    shutil.rmtree(destination)
                shutil.copytree(origin, destination)
            else:
                shutil.copy(origin, destination)
        except shutil.SameFileError:
            pass
        except FileNotFoundError:
            raise FileNotFoundError(f"File {origin} not found.")

    @staticmethod
    def remove_folder(path):
        """ Remove folder. """
        with suppress(PermissionError):
            shutil.rmtree(path)

    @staticmethod
    def remove(path):
        """ Remove file or folder. """
        if not os.path.exists(path):  
            return
        if os.path.isdir(path):
            FileUtils.remove_folder(path)
        else:
            os.unlink(path)

    @staticmethod
    def parse_folder(path) -> str:
        """ Get folder from config. """
        if path is not None and path.startswith(('/', '~')):
            return os.path.expanduser(path)
        else:
            return os.path.join(os.getcwd(), path)

    @staticmethod
    def move(origin, destination):
        """ Move file to destination. """
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        try:
            shutil.move(origin, destination)
        except shutil.Error:
            FileUtils.remove(origin)

class RequestUtils:
    @staticmethod
    def urljoin(*args):
        """ Join url parts. """
        return '/'.join(args).replace('//', '/').replace(':/', '://')

class FileHeaders(Enum):
    XML = '<?xml'
    CLRMAMEPRO = 'clrma'

def show_progress(block_num, block_size, total_size):
    if total_size != -1:
        print(f' {block_num * block_size / total_size:.1%}', end="\r")
    else:
        print(f' {block_num * block_size / 1024 / 1024:.1f} MB', end="\r")

def compare_dates(date1, date2):
    if date1 is None or date2 is None:
        return False
    dayfirst = date1[2] in ['/', '-']
    if isinstance(date1, str):
        date1 = date1.split(' ')[0]
        date1 = parser.parse(date1, fuzzy=True, dayfirst=dayfirst)
    if isinstance(date2, str):
        date2 = date2.split(' ')[0]
        date2 = parser.parse(date2, fuzzy=True, dayfirst=dayfirst)
    return date1 > date2
