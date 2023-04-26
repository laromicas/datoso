"""
    Database module
"""
import os

from typing import Dict, Any
from tinydb import TinyDB, JSONStorage
from tinydb.middlewares import CachingMiddleware

from datoso.helpers import FileUtils
from datoso.configuration import config

database_path = FileUtils.parse_folder(config['PATHS'].get('DatosoPath','~/.datoso'))
os.makedirs(f"{database_path}", exist_ok=True)

DATABASE_URL = os.path.join(database_path, config['PATHS'].get('DatabaseFile','datoso.json'))

class JSONStorageWithBackup(JSONStorage):
    """ TinyDB JSON storage with backup. """
    path: str = DATABASE_URL

    def __init__(self, path: str, create_dirs=False, encoding=None, access_mode='r+', **kwargs):
        self.path = path
        super().__init__(path, create_dirs, encoding, access_mode, **kwargs)

    def write(self, data: Dict[str, Dict[str, Any]]):
        """ Write data to the storage. """
        self.make_backup()
        super().write(data)

    def make_backup(self):
        """ Make a backup of the database. """
        FileUtils.copy(self.path, f"{self.path}.bak")


DB = TinyDB(DATABASE_URL, storage=CachingMiddleware(JSONStorageWithBackup), indent=4)

# DB = TinyDB(DATABASE_URL, storage=JSONStorageWithBackup, indent=4)
