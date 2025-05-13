"""Helper class to manage the folders of the project."""
from pathlib import Path

from datoso.configuration import config
from datoso.helpers.file_utils import parse_path, remove_path


class Folders:
    """Folders class."""

    base: Path = None
    download: Path = None
    dats: Path = None
    backup: Path = None
    extras: list = None

    def __init__(self, seed: str, extras: list | None=None) -> None:
        """Initialize the folders."""
        self.base = parse_path(config['PATHS'].get('DownloadPath'))
        self.download = Path(self.base) / seed
        self.dats = Path(self.download) / 'dats'
        self.backup = Path(self.download) / 'backup'
        extras = extras if extras else []
        self.extras = [] if not extras else [Path(self.dats) / extra for extra in extras]

    def clean_dats(self) -> None:
        """Clean dats folder."""
        remove_path(self.dats)
        Path(self.dats).mkdir(parents=True, exist_ok=True)

    def create_all(self) -> None:
        """Create all folders."""
        self.download.mkdir(parents=True, exist_ok=True)
        self.dats.mkdir(parents=True, exist_ok=True)
        self.backup.mkdir(parents=True, exist_ok=True)
        for extra in self.extras:
            extra.mkdir(parents=True, exist_ok=True)
