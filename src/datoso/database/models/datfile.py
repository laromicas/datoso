"""Database models for the datfile."""
# pylint: disable=too-few-public-methods
from dataclasses import dataclass
from pathlib import PosixPath

from dataclasses_json import dataclass_json

# from pydantic import BaseModel, Extra
from tinydb import Query

from datoso.database import DatabaseSingleton


@dataclass
class Base:
    _table_name = None
    _table = None
    _DB = None

    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)
        self.db_init()

    def db_init(self):
        """Initialize the database."""
        self._DB = DatabaseSingleton()
        self._table = self._DB.DB.table(self._table_name)

    def check_init(self):
        if not self._DB:
            self.db_init()

    def get_one(self):
        """Get a record."""
        self.check_init()
        return self._table.get(self.query())

    def load(self, query=None):
        """Load record from the database."""
        self.check_init()
        result = self._table.search(query or self.query())
        if result:
            self.__dict__.update(result[0])

    def save(self, query=None):
        """Save record to the database."""
        self.check_init()
        if getattr(self, '_id', None):
            query = Query()
            self._table.upsert(self.to_dict(), query.id == self._id)
        else:
            self._id = self._table.upsert(self.to_dict(), query or self.query())

    def to_dict(self):
        """Convert to dictionary."""
        dic = super().to_dict()
        for key, value in dic.items():
            if isinstance(value, PosixPath):
                dic[key] = str(value)
        return {key: value for key, value in dic.items() if value is not None}

    def set_table(self, table_name):
        """Set the table."""
        self._table = table_name

    def get_table(self):
        """Get the table."""
        return self._table

    @classmethod
    def search(cls, query):
        """Search for a record."""
        table_name = cls._table_name
        base = Base(_table_name=table_name)
        return base.get_table().search(query)

    @classmethod
    def all(cls):
        """Get all systems."""
        table_name = cls._table_name
        base = Base(_table_name=table_name)
        return base.get_table().all()

    @classmethod
    def truncate(cls):
        """Truncate the table."""
        table_name = cls._table_name
        base = Base(_table_name=table_name)
        base.get_table().truncate()

    def update(self, *args, **kwargs):
        """Update a record."""
        self._table.update(*args, **kwargs)

    def remove(self, *args, **kwargs):
        """Remove a record."""
        self._table.remove(*args, **kwargs)

    def flush(self):
        """Flush the database."""
        self._table.storage.flush()

    def get_db(self):
        """Get the database."""
        return self._DB


@dataclass_json
@dataclass
class Dat(Base):
    """Dat file model."""

    _table_name = 'dats'
    name: str
    seed: str
    full_name: str | None = None
    modifier: str | None = None
    company: str | None = None
    system: str | None = None
    file: str | None = None
    new_file: str | None = None
    path: str | None = None
    date: str | None = None
    automerge: bool | None = None
    version: str | None = None
    system_type: str | None = None
    status: str | None = None

    def query(self):
        """Query to update or load a record."""
        query = Query()
        return (query.name == self.name) & (query.seed == self.seed)

    def is_enabled(self):
        """Check if the dat is enabled."""
        return self.status is None or self.status == 'enabled'

    def remove(self, **kwargs):
        """Remove a record."""
        self._table.remove(**kwargs)


@dataclass_json
@dataclass
class Seed(Base):
    """Repo file model."""

    _table_name = 'repos'
    name: str

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db_init()

    def query(self):
        """Query to update or load a record."""
        query = Query()
        return query.name == self.name

@dataclass_json
@dataclass
class ExtraConfig:
    """Extra Config file model."""

    empty_suffix: dict | None = None
    if_suffix: dict | None = None

@dataclass_json
@dataclass
class Override:
    """Override file model."""

    company: str | None = None
    system: str | None = None
    modifier: str | None = None
    system_type: str | None = None
    suffix: str | None = None

@dataclass_json
@dataclass
class System(Base):
    """System file model."""

    _table_name = 'systems'
    system: str
    system_type: str | None
    company: str | None = None
    override: Override | None = None
    extra_configs: ExtraConfig | None = None

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db_init()

    def query(self):
        """Query to update or load a record."""
        query = Query()
        return (query.company == self.company) & (query.system == self.system)


@dataclass_json
@dataclass
class MIA(Base):
    """MIA file model."""

    _table_name = 'mia'
    system: str
    game: str
    size: str
    crc32: str
    sha1: str
    md5: str

    def query(self):
        """Query to update or load a record."""
        query = Query()
        if self.sha1:
            return (query.sha1 == self.sha1)
        if self.md5:
            return (query.md5 == self.md5)
        if self.crc32:
            return (query.crc32 == self.crc32)
        return None

if __name__ == '__main__':
    print(System.all())
    ov = Override.from_dict({'company': 'Nintendo', 'system': 'Nintendo 64', 'modifier': 'No-Intro', 'system_type': 'ROM'})
    print(ov)
    print(ov.to_dict())
    ec = ExtraConfig.from_dict({'empty_suffix': {'suffix': ' (Empty)', 'enabled': True}, 'if_suffix': {'suffix': ' (if not empty)', 'enabled': True}})
    print(ec)
    print(ec.to_dict())
    syst = System.from_dict({'system': 'Nintendo 64', 'company': 'Nintendo', 'override': ov, 'extra_configs': ec, 'system_type': 'ROM'})
    print(syst)


