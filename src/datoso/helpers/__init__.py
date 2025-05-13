"""Helpers."""
import re
from numbers import Number
from pathlib import Path

from dateutil import parser


class BcolorsMeta(type):
    """Metaclass for Bcolors."""

    @classmethod
    def __getattr__(cls, name: str) -> str:
        """Get attribute."""
        if name.upper() in Bcolors.color_list():
            def method(text: str) -> str:
                return f'{getattr(Bcolors, name.upper())}{text}{Bcolors.ENDC}'
            return method
        msg = f'module {__name__} has no attribute {name}'
        raise AttributeError(msg)

class Bcolors(metaclass=BcolorsMeta):
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
    # TODO(laromicas): Find replacement for colors below
    # BOLDBLUE = '\e[1;34m'  # noqa: ERA001
    # BOLDCYAN = '\e[1;36m'  # noqa: ERA001
    # BOLDGREEN = '\e[1;32m'  # noqa: ERA001
    # BOLDRED = '\e[1;31m'  # noqa: ERA001
    # BOLDYELLOW = '\e[1;33m'  # noqa: ERA001
    # BOLDWHITE = '\e[1;37m'  # noqa: ERA001
    # BOLDMAGENTA = '\e[1;35m'  # noqa: ERA001

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
    def remove_color(string: str) -> str:
        """Remove color from string."""
        if not string:
            return ''
        for color in Bcolors.color_list():
            string = string.replace(getattr(Bcolors, color), '')
        return string


def is_date(string: str, *, fuzzy: bool | None=None) -> bool:
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

def sizeof_fmt(num: Number, suffix: str='B') -> str:
    """Convert bytes to human readable format."""
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < KB:
            return f'{num:3.1f}{unit}{suffix}'
        num /= KB
    return f'{num: .1f}Yi{suffix}'

def is_git_path(path: str) -> bool:
    """Check if a path is a git repository."""
    pattern = re.compile(r'((git|ssh|http(s)?)|(git@[\w\.]+))(:(//)?)([\w\.@\:/\-~]+)(\.git)(/)?')
    return pattern.match(path)

def is_git_repo(path: str) -> bool:
    """Check if a path is a git repository."""
    return (Path(path) / '.git').is_dir()

def show_progress(block_num: Number, block_size: Number, total_size: Number) -> None:
    """Show download progress."""
    if total_size != -1:
        print(f' {block_num * block_size / total_size:.1%}', end='\r')
    else:
        print(f' {block_num * block_size / 1024 / 1024:.1f} MB', end='\r')

def compare_dates(date1: str | None, date2: str | None) -> bool:
    """Compare two dates."""
    if date1 is None or date2 is None:
        return False
    #replace not_allowed characters for space in dates
    date1 = re.sub(r'[^\w\s\,\-\:]', ' ', date1)
    date2 = re.sub(r'[^\w\s\,\-\:]', ' ', date2)
    dayfirst = date1[2] in ['/', '-']
    try:
        if isinstance(date1, str):
            date1 = parser.parse(date1, fuzzy=True, dayfirst=dayfirst)
            # Prevents bug
            # ValueError: offset must be a timedelta strictly between -timedelta(hours=24) and timedelta(hours=24)
            str(date1)
        if isinstance(date2, str):
            date2 = parser.parse(date2, fuzzy=True, dayfirst=dayfirst)
            # Prevents bug
            # ValueError: offset must be a timedelta strictly between -timedelta(hours=24) and timedelta(hours=24)
            str(date2)
    except ValueError:
        return False
    return date1 > date2
