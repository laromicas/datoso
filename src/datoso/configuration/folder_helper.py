
import os
import shutil
from datoso.helpers import parse_folder
from datoso.configuration import config


class Folders:
    base: str = None
    download: str = None
    dats: str = None
    backup: str = None
    extras: dict = None

    def __init__(self, seed, extras=[]) -> None:
        self.base = parse_folder(config['PATHS'].get('DownloadPath'))
        self.download = os.path.join(self.base, seed)
        self.dats = os.path.join(self.download, 'dats')
        self.backup = os.path.join(self.download, 'backup')
        self.extras = []
        for extra in extras:
            self.extras.append(os.path.join(self.dats, extra))

    def clean_dats(self):
        if os.path.exists(self.dats):
            shutil.rmtree(self.dats)
        os.makedirs(self.dats, exist_ok=True)

    def create_all(self):
        os.makedirs(self.download, exist_ok=True)
        os.makedirs(self.dats, exist_ok=True)
        os.makedirs(self.backup, exist_ok=True)
        for extra in self.extras:
            os.makedirs(extra, exist_ok=True)

