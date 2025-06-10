"""Process actions."""
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

from datoso.configuration import config, logger
from datoso.database.models.dat import Dat
from datoso.helpers import compare_dates
from datoso.helpers.file_utils import copy_path, get_ext, remove_path
from datoso.mias.mia import mark_mias
from datoso.repositories.dat_file import DatFile
from datoso.repositories.dedupe import Dedupe


class Processor:
    """Process actions."""

    _file_dat = None
    _database_dat = None
    actions: list = None
    seed = None
    file = None

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        """Initialize the processor."""
        self._file_data = None
        self.__dict__.update(kwargs)
        if not self.actions:
            self.actions = []

    def process(self) -> Iterator[str]:
        """Process actions."""
        for action in self.actions:
            action_class = globals()[
                action['action']](
                    file=self.file, seed=self.seed, previous=self._file_data,
                    _file_dat=self._file_dat, _database_dat=self._database_dat,
                    **action)
            yield action_class.process()
            self._file_dat = action_class.file_dat
            self._database_dat = action_class.database_dat
            if action_class.stop:
                break


class Process(ABC):
    """Process Base class."""

    _file_dat = None
    _database_dat = None
    status = None
    stop = False

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        """Initialize the process."""
        self.__dict__.update(kwargs)

    @abstractmethod
    def process(self) -> str:
        """Process."""

    def load_file_dat(self) -> dict:
        """Load file."""
        if getattr(self, '_factory', None) and self._factory:
            self._class = self._factory(self.file)
        self._file_dat = self._class(file=self.file, seed=self.seed)
        self._file_dat.load()
        return self._file_dat

    @property
    def file_data(self) -> dict:
        """Get file data."""
        return self.file_dat.dict() if self.file_dat else {}

    @property
    def file_dat(self) -> DatFile:
        """Get file dat."""
        return self._file_dat if self._file_dat else self.load_file_dat()

    def load_database_dat(self) -> Dat:
        """Load database data."""
        self._database_dat = Dat(**self.file_data)
        self._database_dat.load()
        return self._database_dat

    @property
    def database_data(self) -> dict:
        """Get database data."""
        return self.database_dat.to_dict() if self.database_dat else {}

    @property
    def database_dat(self) -> Dat:
        """Get database dat."""
        return self._database_dat if self._database_dat else self.load_database_dat()

    @database_dat.setter
    def database_dat(self, value: Dat | None) -> None:
        self._database_dat = value


class LoadDatFile(Process):
    """Load a dat file."""

    def process(self) -> str:
        """Load a dat file."""
        # If there is a factory method, use it to create the class
        if getattr(self, '_factory', None) and self._factory:
            self._class = self._factory(self.file)

        try:
            if not self._file_dat:
                self.load_file_dat()
            if not self._database_dat:
                self.load_database_dat()
        except Exception as e:  # noqa: BLE001
            self.status = 'Error'
            logger.exception(e)
            return 'Error'
        return 'Loaded'


class DeleteOld(Process):
    """Delete old dat file."""

    def destination(self) -> Path:
        """Parse path."""
        static_path = self.database_dat.static_path if self.database_dat else None
        path = self.file_dat.path if self.file_dat.path is not None else static_path
        if path.startswith(('/', '~')):
            return Path(path).expanduser()
        if not getattr(self, 'folder', None):
            return None
        return Path(self.folder) / path / self.file_dat.file.name \
            if get_ext(self.file_dat.file) in ('.dat', '.xml') \
            else Path(self.folder) / path / self.file_dat.name

    def process(self) -> str:
        """Delete old dat file."""
        try:
            if self.database_data and self.database_data.get('date', None) and self.file_data.get('date', None) \
                and compare_dates(self.database_dat.date, self.file_dat.date):
                self.stop = True
                return 'No Action Taken, Newer Found'
        except ValueError as e:
            logger.exception(e, self.database_dat.date, self.file_dat.date)
            return 'Error'

        if not self.database_data.get('new_file', None):
            return 'New'

        if getattr(self, 'folder', None) and self.database_data.get('date', None):
            old_file = Path(self.database_data.get('new_file', '') or '')
            new_file = self.destination()
            if old_file == new_file \
                and self.database_data.get('date', None) == self.file_data.get('date', None) \
                and not config.getboolean('PROCESS', 'Overwrite', fallback=False) \
                and self.database_dat.is_enabled():
                return 'Exists'

        remove_path(Path(self.database_dat.new_file), remove_empty_parent=True)
        if not self.database_dat.is_enabled():
            self.stop = True
            self.database_dat.new_file = None
            self.database_dat.save()
            self.database_dat.flush()
            return 'Disabled'
        return 'Deleted'


class Copy(Process):
    """Copy files."""

    def destination(self) -> Path:
        """Parse path."""
        static_path = self.database_dat.static_path if self.database_dat else None
        path = self.file_dat.path if self.file_dat.path is not None else static_path
        if path.startswith(('/', '~')):
            return Path(path).expanduser()
        return Path(self.folder) / path / self.file_dat.file.name \
            if get_ext(self.file_dat.file) in ('.dat', '.xml') \
            else Path(self.folder) / path / self.file_dat.name

    def process(self) -> str:
        """Copy files."""
        result = None
        origin = self.file if self.file else None
        destination = self.destination()
        if not self.database_dat:
            copy_path(origin, destination)
            return 'Copied'
        if not self.database_dat.is_enabled():
            self.file_dat.new_file = None
            return 'Ignored'
        old_file = Path(self.database_data.get('new_file', '') or '')
        new_file = destination

        if old_file == new_file and destination.exists() \
            and not config.getboolean('PROCESS', 'Overwrite', fallback=False):
            self.stop = True
            return 'Exists'

        if old_file.name == '':
            result = 'Created'
        elif old_file != new_file:
            result = 'Updated'
        elif config.getboolean('PROCESS', 'Overwrite', fallback=False):
            result = 'Overwritten'
        elif not new_file.exists():
            result = 'Updated'
        else:
            msg = 'Unknown state'
            raise TypeError(msg)

        try:
            if self.database_data \
                and self.database_data.get('date', None) \
                and self.file_data.get('date', None) \
                and compare_dates(self.database_dat.date, self.file_dat.date):
                return 'No Action Taken, Newer Found'

            self.database_dat.new_file = destination
            copy_path(origin, destination)
        except ValueError:
            pass
        return result


class SaveToDatabase(Process):
    """Save process to database."""

    def process(self) -> str:
        """Save process to database."""
        try:
            data_to_save = {**self.database_data, **self.file_data}
            instance = Dat(**data_to_save)
            instance.save()
            instance.flush()
            self._database_dat = instance
        except Exception as e:  # noqa: BLE001
            logger.exception(e)
            return 'Error'
        else:
            return 'Saved'


class MarkMias(Process):
    """Mark missing in action."""

    def process(self) -> str:
        """Mark missing in action."""
        if not config.getboolean('PROCESS', 'ProcessMissingInAction', fallback=False):
            return 'Skipped'
        mark_mias(dat_file=self.database_dat.new_file)
        return 'Marked'


class AutoMerge(Process):
    """Save process to database."""

    child_db = None

    def process(self) -> str:
        """Save process to database."""
        if getattr(self.database_dat, 'automerge', None):
            merged = Dedupe(self.database_dat)
        else:
            return 'Skipped'
        if merged.dedupe() > 0:
            merged.save()
            return 'Automerged'
        return 'Skipped'


class Deduplicate(Process):
    """Save process to database."""

    def process(self) -> str:
        """Save process to database."""
        if parent := getattr(self.database_dat, 'parent', None):
            merged = Dedupe(self.database_dat, parent)
        else:
            return 'Skipped'
        if merged.dedupe() > 0:
            merged.save()
            return 'Deduped'
        return 'Skipped'



if __name__ == '__main__':
    procesor = Processor()
    procesor.process()
