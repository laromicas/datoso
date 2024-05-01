"""Process actions."""
import shutil
from contextlib import suppress
from pathlib import Path

from datoso.configuration import config, logger
from datoso.database.models.datfile import Dat
from datoso.helpers import FileUtils, compare_dates
from datoso.repositories.dedupe import Dedupe


class Processor:
    """Process actions."""

    _previous = None
    actions: list = None
    seed = None
    file = None

    def __init__(self, **kwargs):
        self._previous = None
        self.__dict__.update(kwargs)
        if not self.actions:
            self.actions = []

    def process(self):
        """Process actions."""
        for action in self.actions:
            action_class = globals()[action['action']](file=self.file, seed=self.seed, previous=self._previous, **action)
            yield action_class.process()
            self._previous = action_class.output
            if action_class.stop:
                break


class Process:
    """Process Base class."""

    output = None
    status = None
    stop = False
    previous: dict = None
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class LoadDatFile(Process):
    """Load a dat file."""

    # pylint: disable=no-member
    class_name = None
    file = None
    seed = None
    database = None
    _class = None
    _factory = None
    _dat = None

    def process(self):
        """Load a dat file."""
        from datoso.database.models.datfile import Dat

        # If there is a factory method, use it to create the class
        if getattr(self, '_factory', None) and self._factory:
            self._class = self._factory(self.file)

        try:
            self._dat = self._class(file=self.file)
            self._dat.load()
            self.database = Dat(seed=str(self.seed), **self._dat.dict())
            self.output = self.database.to_dict()
        except Exception as e:
            self._dat = None
            self.status = 'Error'
            logger.exception(e)
            return 'Error'
        return 'Loaded'


class DeleteOld(Process):
    """Delete old dat file."""

    database = None
    def process(self):
        """Delete old dat file."""
        from datoso.database.models.datfile import Dat
        self.database = Dat(seed=self.previous['seed'], name=self.previous['name'])
        self.database.load()
        olddat = self.database.to_dict()
        try:
            if self.previous and getattr(self.database, 'date', None) and self.previous.get('date', None) and compare_dates(self.database.date, self.previous['date']):
                result = 'No Action Taken, Newer Found'
                self.stop = True
                return result
        except ValueError as e:
            logger.exception(e)
            print(self.database.date, self.previous['date'])
            return 'Error'

        result = None
        if olddat.get('new_file'):
            try:
                shutil.rmtree(olddat['new_file'])
            except NotADirectoryError:
                with suppress(FileNotFoundError):
                    Path(olddat['new_file']).unlink()
            except FileNotFoundError:
                pass
            if not self.database.is_enabled():
                self.stop = True
            result = 'Deleted'

        self.output = self.previous
        return result


class Copy(Process):
    """Copy files."""

    destination = None
    file = None
    folder = None
    database = None

    def process(self):
        """Copy files."""
        from datoso.database.models.datfile import Dat
        origin = self.file if self.file else None
        filename = Path(origin).name
        self.destination = self.destination if self.destination else self.previous['path']

        destination = Path(self.folder) / self.destination / filename if filename.endswith(('.dat', '.xml')) else Path(self.folder) / self.destination / self.previous['name']

        result = None
        self.output = self.previous
        if not self.previous:
            FileUtils.copy(origin, destination)
            return 'Copied'
        self.database = Dat(seed=self.previous['seed'], name=self.previous['name'])
        self.database.load()
        if not self.database.is_enabled():
            self.previous['new_file'] = None
            return 'Ignored'

        old_file = Path(self.database.to_dict().get('new_file', '') or '')
        new_file = destination

        if old_file == new_file and destination.exists() and not config.getboolean('GENERAL', 'Overwrite', fallback=False):
            return 'Exists'

        if not old_file:
            result = 'Created'
        elif old_file != new_file:
            result = 'Updated'
        elif config.getboolean('GENERAL', 'Overwrite', fallback=False):
            result = 'Overwritten'

        try:
            if getattr(self.database, 'date', None) and self.previous.get('date', None) and compare_dates(self.database.date, self.previous['date']):
                result = 'No Action Taken, Newer Found'
            else:
                self.previous['new_file'] = destination
                FileUtils.copy(origin, destination)
        except ValueError:
            pass

        self.output = self.previous
        return result


class MarkMias(Process):
    """Mark missing in action."""

    database = None
    def process(self):
        """Mark missing in action."""
        self.output = self.previous
        if not config.getboolean('PROCESS', 'ProcessMissingInAction', fallback=False):
            return 'Skipped'
        from datoso.mias.mia import mark_mias
        database = Dat(seed=self.previous['seed'], name=self.previous['name'])
        database.load()

        if not database.is_enabled():
            return 'Ignored'
        mark_mias(dat_file=self.previous['new_file'])
        return 'Marked'


class SaveToDatabase(Process):
    """Save process to database."""

    database = None
    def process(self):
        """Save process to database."""
        from datoso.database.models.datfile import Dat
        self.database = Dat(**self.previous)
        self.database.save()
        self.database.flush()
        self.output = self.previous
        return 'Saved'


class Deduplicate(Process):
    """Save process to database."""

    parent_db = None
    child_db = None

    def get_dat(self, name, seed):
        """Get dat file."""
        from datoso.database.models.datfile import Dat
        dat = Dat(name=name, seed=seed)
        dat.load()
        return dat

    def process(self):
        """Save process to database."""
        child_db = Dat(**self.previous)
        child_db.load()
        if parent := getattr(child_db, 'parent', None):
            merged = Dedupe(child_db, parent)
        elif getattr(child_db, 'automerge', None):
            merged = Dedupe(child_db)
        else:
            return 'Skipped'

        merged.dedupe()
        merged.save()
        self.output = self.previous
        return 'Deduped'


if __name__ == '__main__':
    procesor = Processor()
    procesor.process()
