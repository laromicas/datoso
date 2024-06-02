"""Helpers"""
import re
import shutil
from contextlib import suppress
from enum import Enum
from pathlib import Path

from dateutil import parser


class Bcolors:
    # pylint: disable=anomalous-backslash-in-string
    """Color class."""

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
    BOLDBLUE = r'\e[1;34m'
    BOLDCYAN = r'\e[1;36m'
    BOLDGREEN = r'\e[1;32m'
    BOLDRED = r'\e[1;31m'
    BOLDYELLOW = r'\e[1;33m'
    BOLDWHITE = r'\e[1;37m'
    BOLDMAGENTA = r'\e[1;35m'

    @staticmethod
    def color_list() -> list:
        """Return list of colors."""
        return [attr for attr in Bcolors.__dict__ if not callable(getattr(Bcolors, attr)) and not attr.startswith('__')]

    @staticmethod
    def no_color() -> None:
        """Disables color output."""
        for color in Bcolors.color_list():
            setattr(Bcolors, color, '')

    @staticmethod
    def remove_color(string) -> str:
        """Remove color from string."""
        if not string:
            return ''
        for color in Bcolors.color_list():
            string = string.replace(getattr(Bcolors, color), '')
        return string

def is_date(string, fuzzy=None) -> bool:
    """Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parser.parse(string, fuzzy=fuzzy or False)
    except ValueError:
        return False
    return True

KB = 1024

def sizeof_fmt(num, suffix='B') -> str:
    """Convert bytes to human readable format."""
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < KB:
            return f'{num:3.1f}{unit}{suffix}'
        num /= KB
    return f'{num: .1f}Yi{suffix}'

def is_git_path(path) -> bool:
    """Check if a path is a git repository."""
    pattern = re.compile(r'((git|ssh|http(s)?)|(git@[\w\.]+))(:(//)?)([\w\.@\:/\-~]+)(\.git)(/)?')
    return pattern.match(path)

def is_git_repo(path) -> bool:
    """Check if a path is a git repository."""
    if Path(Path(path) / '.git').is_dir():
        return True
    return False

class FileUtils:

    @staticmethod
    def copy(origin, destination):
        """Copy file to destination."""
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        try:
            if Path(origin).is_dir():
                with suppress(FileNotFoundError):
                    shutil.rmtree(destination)
                shutil.copytree(origin, destination)
            else:
                shutil.copy(origin, destination)
        except shutil.SameFileError:
            pass
        except FileNotFoundError:
            msg = f'File {origin} not found.'
            raise FileNotFoundError(msg) from None

    @staticmethod
    def remove_folder(path: str | Path):
        """Remove folder."""
        with suppress(PermissionError):
            shutil.rmtree(path)

    @staticmethod
    def remove(pathstring: str | Path, remove_empty_parent = None) -> None:
        path = pathstring if isinstance(pathstring, Path) else FileUtils.parse_path(pathstring)
        """Remove file or folder."""
        if not path.exists():
            return
        if path.is_dir():
            FileUtils.remove_folder(path)
        else:
            path.unlink()
        if remove_empty_parent and not list(path.parent.iterdir()):
            FileUtils.remove(path.parent, remove_empty_parent)

    @staticmethod
    def parse_path(path: str) -> Path:
        """Get folder from config."""
        path = path if path is not None else ''
        if path.startswith(('/', '~')):
            return Path(path).expanduser()
        return Path.cwd() / path

    @staticmethod
    def move(origin, destination):
        """Move file to destination."""
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(origin, destination)
        except shutil.Error:
            FileUtils.remove(origin)

    @staticmethod
    def get_ext(path: str | Path):
        """Get extension of file."""
        return Path(path).suffix

class RequestUtils:
    @staticmethod
    def urljoin(*args):
        """Join url parts."""
        return '/'.join(args).replace('//', '/').replace(':/', '://')

class FileHeaders(Enum):
    XML = '<?xml'
    CLRMAMEPRO = 'clrma'
    DOSCENTER = 'DOSCe'

def show_progress(block_num, block_size, total_size):
    if total_size != -1:
        print(f' {block_num * block_size / total_size:.1%}', end='\r')
    else:
        print(f' {block_num * block_size / 1024 / 1024:.1f} MB', end='\r')

def compare_dates(date1, date2):
    if date1 is None or date2 is None:
        return False
    #replace not_allowed characters for space in dates
    date1 = re.sub(r'[^\w\s\,\-\:]', ' ', date1)
    date2 = re.sub(r'[^\w\s\,\-\:]', ' ', date1)
    dayfirst = date1[2] in ['/', '-']
    try:
        if isinstance(date1, str):
            date1 = parser.parse(date1, fuzzy=True, dayfirst=dayfirst)
        if isinstance(date2, str):
            date2 = parser.parse(date2, fuzzy=True, dayfirst=dayfirst)
    except ValueError:
        return False
    return date1 > date2
