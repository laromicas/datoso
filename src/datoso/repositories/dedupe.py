import logging
from pathlib import Path

from datoso.database.models.dat import Dat
from datoso.repositories.dat_file import DatFile


class DatDedupe:
    _datdb: Dat
    _datfile: DatFile
    _file: str | Path

    @property
    def datdb(self) -> Dat:
        return self._db

    @datdb.setter
    def datdb(self, value):
        self._db = value

    @property
    def datfile(self) -> DatFile:
        return self._datfile

    @datfile.setter
    def datfile(self, value):
        self._datfile = value

    @property
    def file(self) -> str | Path:
        return self._file

    @file.setter
    def file(self, value):
        self._file = value


class Dedupe:
    """Merge two dat files."""

    child: DatDedupe
    parent: DatDedupe | None

    def __init__(self, child, parent=None):
        """Initialize Dedupe."""
        self.child = DatDedupe()
        self.parent = DatDedupe() if parent else None

        def load_metadata(var, obj):
            if isinstance(var, str):
                if ':' in var:
                    splitted = var.split(':')
                    seed = splitted[0]
                    name = splitted[1]
                    obj.datdb = Dat(name=name, seed=seed)
                    obj.datdb.load()
                    var = obj.datdb
                elif var.endswith(('.dat', '.xml')):
                    obj.file = var
                else:
                    msg = 'Invalid dat file'
                    raise LookupError(msg)
            if isinstance(var, Dat):
                obj.datdb = var
                obj.file = getattr(var, 'new_file', None) or var.file
            if isinstance(var, DatFile):
                obj.datfile = var
            else:
                obj.datfile = self.get_dat_file(obj.file)

        load_metadata(child, self.child)
        if parent:
            load_metadata(parent, self.parent)

    def get_dat_file(self, file):
        try:
            dat = DatFile.from_file(file)
            dat.load()
        except Exception:
            msg = 'Invalid dat file'
            raise ValueError(msg) from None
        return dat

    def dedupe(self):
        if self.parent:
            self.child.datfile.merge_with(self.parent.datfile)
        else:
            self.child.datfile.dedupe()
        logging.info('Deduped %i roms', len(self.child.datfile.merged_roms))
        return len(self.child.datfile.merged_roms)

    def save(self, file=None):
        if file:
            self.child.datfile.file = file
        self.child.datfile.save()
