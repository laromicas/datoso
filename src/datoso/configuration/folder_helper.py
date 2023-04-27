
import os
from datoso.helpers import FileUtils
from datoso.configuration import config


class Folders:
    base: str = None
    download: str = None
    dats: str = None
    backup: str = None
    extras: dict = None

    def __init__(self, seed, extras=[]) -> None:
        self.base = FileUtils.parse_folder(config['PATHS'].get('DownloadPath'))
        self.download = os.path.join(self.base, seed)
        self.dats = os.path.join(self.download, 'dats')
        self.backup = os.path.join(self.download, 'backup')
        self.extras = []
        for extra in extras:
            self.extras.append(os.path.join(self.dats, extra))

    def clean_dats(self):
        FileUtils.remove(self.dats)
        os.makedirs(self.dats, exist_ok=True)

    def create_all(self):
        os.makedirs(self.download, exist_ok=True)
        os.makedirs(self.dats, exist_ok=True)
        os.makedirs(self.backup, exist_ok=True)
        for extra in self.extras:
            os.makedirs(extra, exist_ok=True)

