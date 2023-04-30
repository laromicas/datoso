"""
    Database models for the datfile.
"""
# pylint: disable=too-few-public-methods
from typing import Optional

from pydantic import BaseModel, Extra
from tinydb import Query
from datoso.database import DB

class Database:
    """ TinyDB wrapper (). """
    DB = DB
    table = None

class DatabaseModel(BaseModel): # BaseModel needed for initialization, TODO: find a better way
    """ Base model for TinyDB. """
    class Config:
        """ Pydantic default config. """
        extra = Extra.allow
        arbitrary_types_allowed = True

    _DB = Database()
    _id: int = None
    _table_name: str = None

    def __init__(self, **kwargs) -> None:
        self._DB.DB = DB  # pylint: disable=invalid-name
        self._DB.table = DB.table(self._table_name)
        super().__init__(**kwargs)

    def load(self):
        """ Load record from the database. """
        result = self._DB.table.search(self.query())
        if result:
            self.__dict__.update(result[0])

    def save(self):
        """ Save record to the database. """
        query = Query()
        if self._id:
            self._DB.table.upsert(self.dict(), query.id == self._id)
        else:
            self._id = self._DB.table.upsert(self.dict(), self.query())

    def query(self):
        """ Query to update or load a record. """
        query = Query()
        return query.id == self._id

    def close(self):
        """ Close the database. """
        self._DB.table.storage.flush()



class Dat(DatabaseModel):
    """ Dat file model. """
    _table_name = 'dats'
    name: str
    modifier: Optional[str]
    company: Optional[str]
    system: Optional[str]
    seed: str

    def query(self):
        """ Query to update or load a record. """
        query = Query()
        return (query.name == self.name) & (query.seed == self.seed)

    def is_enabled(self):
        """ Check if the dat is enabled. """
        return not getattr(self, 'status', None) or self.status == 'enabled' # pylint: disable=no-member


class Seed(DatabaseModel):
    """ Repo file model. """
    _table_name = 'repos'
    name: str

    def query(self):
        """ Query to update or load a record. """
        query = Query()
        return query.name == self.name

class System(DatabaseModel):
    """ System file model. """
    _table_name = 'systems'
    company: Optional[str]
    system: str

    def query(self):
        """ Query to update or load a record. """
        query = Query()
        return (query.company == self.company) & (query.system == self.system)

    @staticmethod
    def all():
        """ Get all systems. """
        System._DB.DB = DB  # pylint: disable=invalid-name
        System._DB.table = DB.table(System._table_name)
        return System._DB.table.all()