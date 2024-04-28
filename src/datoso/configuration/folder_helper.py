
from pathlib import Path

from datoso.configuration import config
from datoso.helpers import FileUtils


class Folders:
    base: Path = None
    download: Path = None
    dats: Path = None
    backup: Path = None
    extras: list = None

    def __init__(self, seed, extras=None) -> None:
        self.base = FileUtils.parse_folder(config['PATHS'].get('DownloadPath'))
        self.download = Path(self.base) / seed
        self.dats = Path(self.download) / 'dats'
        self.backup = Path(self.download) / 'backup'
        extras = extras if extras else []
        self.extras = [] if not extras else [Path(self.dats) / extra for extra in extras]

    def clean_dats(self):
        FileUtils.remove(self.dats)
        Path(self.dats).mkdir(parents=True, exist_ok=True)

    def create_all(self):
        self.download.mkdir(parents=True, exist_ok=True)
        self.dats.mkdir(parents=True, exist_ok=True)
        self.backup.mkdir(parents=True, exist_ok=True)
        for extra in self.extras:
            extra.mkdir(parents=True, exist_ok=True)
