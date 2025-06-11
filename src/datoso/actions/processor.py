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
            logger.info(f"Processing action: [bold cyan]{action['action']}[/bold cyan]")
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
        logger.info(f"Loading DAT file: [bold magenta]{self.file}[/bold magenta]")
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
            logger.exception(f"Error loading DAT file [bold red]{self.file}[/bold red]: {e}")
            return 'Error'
        logger.info(f"DAT file [bold green]{self.file}[/bold green] loaded successfully.")
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
                logger.info(f"Skipping delete for [bold magenta]{self.file_dat.name}[/bold magenta], newer version found in database.")
                return 'No Action Taken, Newer Found'
        except ValueError as e:
            logger.exception(f"Error comparing dates for [bold red]{self.file_dat.name}[/bold red]: {e}")
            return 'Error'

        if not self.database_data.get('new_file', None):
            logger.info(f"No old file found for [bold magenta]{self.file_dat.name}[/bold magenta], nothing to delete.")
            return 'New'

        old_file_path_str = self.database_data.get('new_file', '')
        old_file_path = Path(old_file_path_str or '')
        destination_path = self.destination()

        if getattr(self, 'folder', None) and self.database_data.get('date', None):
            if old_file_path == destination_path \
                and self.database_data.get('date', None) == self.file_data.get('date', None) \
                and not config.getboolean('PROCESS', 'Overwrite', fallback=False) \
                and self.database_dat.is_enabled():
                logger.info(f"File [bold magenta]{old_file_path}[/bold magenta] already exists and is up-to-date.")
                return 'Exists'

        logger.info(f"Deleting old file: [bold magenta]{old_file_path}[/bold magenta]")
        remove_path(old_file_path, remove_empty_parent=True)

        if not self.database_dat.is_enabled():
            self.stop = True
            self.database_dat.new_file = None
            self.database_dat.save()
            self.database_dat.flush()
            logger.info(f"DAT file [bold magenta]{self.file_dat.name}[/bold magenta] is disabled, removed from filesystem.")
            return 'Disabled'
        logger.info(f"Old file [bold green]{old_file_path}[/bold green] deleted successfully.")
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
        logger.info(f"Copying file from [bold magenta]{origin}[/bold magenta] to [bold magenta]{destination}[/bold magenta]")

        if not self.database_dat:
            copy_path(origin, destination)
            logger.info(f"File [bold green]{origin}[/bold green] copied to [bold green]{destination}[/bold green] (no database entry).")
            return 'Copied'

        if not self.database_dat.is_enabled():
            self.file_dat.new_file = None
            logger.info(f"DAT file [bold magenta]{self.file_dat.name}[/bold magenta] is disabled, copy ignored.")
            return 'Ignored'

        old_file_path_str = self.database_data.get('new_file', '')
        old_file_path = Path(old_file_path_str or '')

        if old_file_path == destination and destination.exists() \
            and not config.getboolean('PROCESS', 'Overwrite', fallback=False):
            self.stop = True
            logger.info(f"File [bold magenta]{destination}[/bold magenta] already exists and is up-to-date.")
            return 'Exists'

        if old_file_path.name == '':
            result = 'Created'
            logger.info(f"Creating new file: [bold magenta]{destination}[/bold magenta]")
        elif old_file_path != destination:
            result = 'Updated'
            logger.info(f"Updating file path from [bold magenta]{old_file_path}[/bold magenta] to [bold magenta]{destination}[/bold magenta]")
        elif config.getboolean('PROCESS', 'Overwrite', fallback=False):
            result = 'Overwritten'
            logger.info(f"Overwriting existing file: [bold magenta]{destination}[/bold magenta]")
        elif not destination.exists():
            result = 'Updated' # Or 'Created' if old_file_path was also empty, though covered by first case
            logger.info(f"Destination file [bold magenta]{destination}[/bold magenta] does not exist, creating/updating.")
        else:
            msg = f"Unknown state for copy operation: old_file='{old_file_path}', new_file='{destination}'"
            logger.error(msg)
            raise TypeError(msg)

        try:
            if self.database_data \
                and self.database_data.get('date', None) \
                and self.file_data.get('date', None) \
                and compare_dates(self.database_dat.date, self.file_dat.date):
                logger.info(f"Skipping copy for [bold magenta]{self.file_dat.name}[/bold magenta], newer version found in database.")
                return 'No Action Taken, Newer Found'

            self.database_dat.new_file = str(destination)
            copy_path(origin, destination)
            logger.info(f"File [bold green]{origin}[/bold green] copied to [bold green]{destination}[/bold green] successfully.")
        except ValueError: # Assuming this is for date comparison errors
            logger.exception("Error comparing dates during copy operation.")
            pass # Or return 'Error'
        except Exception as e:
            logger.exception(f"Error copying file [bold red]{origin}[/bold red] to [bold red]{destination}[/bold red]: {e}")
            return 'Error' # Ensure errors during copy are reported
        return result


class SaveToDatabase(Process):
    """Save process to database."""

    def process(self) -> str:
        """Save process to database."""
        dat_name = self.file_data.get('name', 'Unknown DAT')
        logger.info(f"Saving data for [bold magenta]{dat_name}[/bold magenta] to database.")
        try:
            data_to_save = {**self.database_data, **self.file_data}
            # Ensure new_file is a string for Pydantic model
            if 'new_file' in data_to_save and isinstance(data_to_save['new_file'], Path):
                data_to_save['new_file'] = str(data_to_save['new_file'])
            instance = Dat(**data_to_save)
            instance.save()
            instance.flush()
            self._database_dat = instance
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Error saving data for [bold red]{dat_name}[/bold red] to database: {e}")
            return 'Error'
        else:
            logger.info(f"Data for [bold green]{dat_name}[/bold green] saved to database successfully.")
            return 'Saved'


class MarkMias(Process):
    """Mark missing in action."""

    def process(self) -> str:
        """Mark missing in action."""
        dat_name = self.database_dat.name if self.database_dat else 'Unknown DAT'
        if not config.getboolean('PROCESS', 'ProcessMissingInAction', fallback=False):
            logger.info(f"Skipping MIA processing for [bold magenta]{dat_name}[/bold magenta] (disabled in config).")
            return 'Skipped'
        logger.info(f"Marking MIAs for DAT file: [bold magenta]{self.database_dat.new_file}[/bold magenta]")
        try:
            mark_mias(dat_file=self.database_dat.new_file)
        except Exception as e:
            logger.exception(f"Error marking MIAs for [bold red]{self.database_dat.new_file}[/bold red]: {e}")
            return 'Error'
        logger.info(f"MIAs marked for [bold green]{self.database_dat.new_file}[/bold green] successfully.")
        return 'Marked'


class AutoMerge(Process):
    """Save process to database."""

    child_db = None

    def process(self) -> str:
        """Save process to database."""
        dat_name = self.database_dat.name if self.database_dat else 'Unknown DAT'
        if getattr(self.database_dat, 'automerge', None):
            logger.info(f"Attempting automerge for [bold magenta]{dat_name}[/bold magenta].")
            merged = Dedupe(self.database_dat)
        else:
            logger.info(f"Skipping automerge for [bold magenta]{dat_name}[/bold magenta] (not configured for automerge).")
            return 'Skipped'
        try:
            if merged.dedupe() > 0:
                merged.save()
                logger.info(f"Automerge successful for [bold green]{dat_name}[/bold green].")
                return 'Automerged'
        except Exception as e:
            logger.exception(f"Error during automerge for [bold red]{dat_name}[/bold red]: {e}")
            return 'Error'
        logger.info(f"No changes made during automerge for [bold magenta]{dat_name}[/bold magenta].")
        return 'Skipped'


class Deduplicate(Process):
    """Save process to database."""

    def process(self) -> str:
        """Save process to database."""
        dat_name = self.database_dat.name if self.database_dat else 'Unknown DAT'
        if parent := getattr(self.database_dat, 'parent', None):
            logger.info(f"Attempting deduplication for [bold magenta]{dat_name}[/bold magenta] with parent [bold magenta]{parent.name}[/bold magenta].")
            merged = Dedupe(self.database_dat, parent)
        else:
            logger.info(f"Skipping deduplication for [bold magenta]{dat_name}[/bold magenta] (no parent found).")
            return 'Skipped'
        try:
            if merged.dedupe() > 0:
                merged.save()
                logger.info(f"Deduplication successful for [bold green]{dat_name}[/bold green].")
                return 'Deduped'
        except Exception as e:
            logger.exception(f"Error during deduplication for [bold red]{dat_name}[/bold red]: {e}")
            return 'Error'
        logger.info(f"No changes made during deduplication for [bold magenta]{dat_name}[/bold magenta].")
        return 'Skipped'



if __name__ == '__main__':
    procesor = Processor()
    procesor.process()
