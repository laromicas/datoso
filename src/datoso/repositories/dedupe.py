"""Dedupe module."""
import logging
from pathlib import Path

from datoso.database.models.dat import Dat
from datoso.repositories.dat_file import ClrMameProDatFile, DatFile


class DatDedupe:
    """Dat Dedupe class."""

    _datdb: Dat
    _datfile: DatFile
    _file: str | Path
    datfiles: list[DatFile]

    @property
    def datdb(self) -> Dat:
        """Return the dat database."""
        return self._db

    @datdb.setter
    def datdb(self, value: Dat) -> None:
        """Set the dat database."""
        self._db = value

    @property
    def datfile(self) -> DatFile:
        """Return the dat file."""
        return self._datfile

    @datfile.setter
    def datfile(self, value: DatFile) -> None:
        """Set the dat file."""
        self._datfile = value

    @property
    def file(self) -> str | Path:
        """Return the file."""
        return self._file

    @file.setter
    def file(self, value: str | Path) -> None:
        """Set the file."""
        self._file = value


class Dedupe:
    """Merge two dat files."""

    child: DatDedupe
    parent: DatDedupe | None

    def __init__(self, child: str | Dat | DatFile, parent: str | Dat | DatFile=None) -> None:
        """Initialize Dedupe."""
        self.child = DatDedupe()
        self.parent = DatDedupe() if parent else None

        def load_metadata(var: str | Dat | DatFile, obj: DatDedupe) -> None:
            if isinstance(var, str):
                if ':' in var:
                    splitted = var.split(':')
                    seed = splitted[0]
                    name = splitted[1]
                    obj.datdb = Dat(name=name, seed=seed)
                    obj.datdb.load()
                    var = obj.datdb
                elif var.endswith(('.dat', '.xml')) or Path(var).is_dir():
                    obj.file = var
                else:
                    msg = 'Invalid dat file'
                    raise LookupError(msg)
            if isinstance(var, Dat):
                obj.datdb = var
                obj.file = getattr(var, 'new_file', None) or var.file
            obj.datfiles = [var] if isinstance(var, DatFile) else \
                [self.get_dat_file(file) for file in self.dats_in(obj.file)]
            obj.datfile = obj.datfiles[0] if obj.datfiles else None

        load_metadata(child, self.child)
        if parent:
            load_metadata(parent, self.parent)

    @staticmethod
    def dats_in(file: str | Path) -> list[Path]:
        """Every .dat/.xml under a directory DAT (recursively), or just the file itself."""
        if not Path(file).is_dir():
            return [Path(file)]
        return sorted(path for path in Path(file).rglob('*')
                      if path.is_file() and path.suffix.lower() in ('.dat', '.xml'))

    def get_dat_file(self, file: str | Path) -> DatFile:
        """Return a DatFile from a file."""
        try:
            dat = DatFile.from_file(file=file)
            if isinstance(dat, ClrMameProDatFile):
                dat.load(load_games=True)
            else:
                dat.load(load_games=True)
        except Exception as e:  # noqa: BLE001
            msg = 'Invalid dat file'
            raise ValueError(msg, e) from None
        return dat

    def dedupe(self) -> int:
        """Dedupe each child DAT (against every parent DAT, if any); return the ROMs removed."""
        for datfile in self.child.datfiles:
            if self.parent:
                for parent in self.parent.datfiles:
                    datfile.merge_with(parent)
            else:
                datfile.dedupe()
        merged = sum(len(datfile.merged_roms) for datfile in self.child.datfiles)
        logging.info('Deduped %i roms', merged)
        return merged

    def save(self, file: str | Path | None = None) -> None:
        """Save the dat file; for a directory DAT, every DAT that changed (in place)."""
        if len(self.child.datfiles) == 1:
            datfile = self.child.datfile
            if file and len(datfile.merged_roms) > 0:
                datfile.file = file
            datfile.save()
            return
        if file:
            msg = 'An output file only works with a single DAT, not a directory of DATs'
            raise ValueError(msg)
        for datfile in self.child.datfiles:
            if datfile.merged_roms:
                datfile.save()
