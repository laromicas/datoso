"""Database module"""
from pathlib import PosixPath
from threading import Lock
from typing import Any

from tinydb import JSONStorage, TinyDB
from tinydb.middlewares import CachingMiddleware

from datoso.configuration import config
from datoso.helpers import FileUtils

database_path = FileUtils.parse_folder(config['PATHS'].get('DatosoPath','~/.datoso'))
database_path.mkdir(parents=True, exist_ok=True)

DATABASE_URL = str(database_path / config['PATHS'].get('DatabaseFile','datoso.json'))

class Types:
    str = str
    int = int
    float = float
    bool = bool
    list = list
    dict = dict
    any = Any
    PosixPath = PosixPath

class JSONStorageWithBackup(JSONStorage):
    """TinyDB JSON storage with backup."""

    path: str = DATABASE_URL

    def __init__(self, path: str, create_dirs=False, encoding=None, access_mode='r+', **kwargs):
        self.path = path
        super().__init__(path, create_dirs, encoding, access_mode, **kwargs)

    def sanitize_data(self, data):
        """Sanitize recursively data before writing to the storage."""
        match type(data):
            case Types.str, Types.int, Types.float, Types.bool:
                return data
            case Types.dict:
                for key, value in data.items():
                    data[key] = self.sanitize_data(value)
                return data
            case Types.list:
                return [self.sanitize_data(item) for item in data]
            case Types.PosixPath:
                return str(data)
            case _:
                return data

    def remove_nulls(self, data):
        """Remove null values from the data."""
        if isinstance(data, dict):
            return {k: self.remove_nulls(v) for k, v in data.items() if v is not None}
        elif isinstance(data, list):
            return [self.remove_nulls(v) for v in data if v is not None]
        return data

    def write(self, data: dict[str, dict[str, Any]]):
        """Write data to the storage."""
        self.make_backup()
        data = self.sanitize_data(data)
        # data = self.remove_nulls(data)
        super().write(data)

    def make_backup(self):
        """Make a backup of the database."""
        FileUtils.copy(self.path, f'{self.path}.bak')


class DatabaseSingletonMeta(type):
    """The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """

    _instances = {} # noqa: RUF012
    _lock: Lock = Lock()
    """
    We now have a lock object that will be used to synchronize threads during
    first access to the Singleton.
    """

    def __call__(cls, *args, **kwargs):
        """Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        with cls._lock:
            # The first thread to acquire the lock, reaches this conditional,
            # goes inside and creates the Singleton instance. Once it leaves the
            # lock block, a thread that might have been waiting for the lock
            # release may then enter this section. But since the Singleton field
            # is already initialized, the thread won't create a new object.
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class DatabaseSingleton(metaclass=DatabaseSingletonMeta):
    DB = None
    def __init__(self) -> None:
        self.DB = TinyDB(DATABASE_URL, storage=CachingMiddleware(JSONStorageWithBackup), indent=4)
        self.table = None
