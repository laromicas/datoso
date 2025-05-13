"""Logging configuration for datoso."""
import logging

from datoso.helpers import Bcolors
from datoso.helpers.file_utils import parse_path

from .configuration import config

log_level = config['LOG'].get('LogLevel', logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s - %(levelname)s] - %(message)s', '%Y-%m-%d %H:%M:%S')

class TrimmedFileHandler(logging.FileHandler):
    """File handler that removes color codes from the log message."""

    def emit(self, record: str) -> None:
        """Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        # Get the log message
        msg = self.format(record).strip()

        # Write the trimmed message to the file
        if msg:
            try:
                self.stream.write(Bcolors.remove_color(msg) + self.terminator)
                self.flush()
            except Exception:  # noqa: BLE001
                self.handleError(record)



class TrimmedStreamHandler(logging.StreamHandler):
    """Stream handler that allows to stdout while logging."""

    def emit(self, record: str) -> None:
        """Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            msg = self.format(record)
            stream = self.stream
            # issue 35046: merged two stream.writes into one.
            stream.write(msg)
            self.flush()
        except RecursionError:  # See issue 36272
            raise
        except Exception:  # noqa: BLE001
            self.handleError(record)

# Get root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def enable_logging() -> None:
    """Enable logging to file."""
    log_path = parse_path(config.get('PATHS','DatosoPath', fallback='~/.config/datoso'))
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / config['LOG'].get('LogFile', 'datoso.log')
    file_handler = TrimmedFileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Create a file handler
if config.getboolean('LOG', 'Logging', fallback=False):
    enable_logging()

# Create a stream handler
stream_handler = TrimmedStreamHandler()
stream_handler.setLevel(logging.INFO)
if config.getboolean('COMMAND', 'Verbose', fallback=False):
    stream_handler.setLevel(logging.DEBUG)
if config.getboolean('COMMAND', 'Quiet', fallback=False):
    stream_handler.setLevel(logging.WARNING)
logger.addHandler(stream_handler)

def set_verbosity(verbosity: int | str) -> None:
    """Set the log level of the stream handler."""
    stream_handler.setLevel(verbosity)

def set_quiet() -> None:
    """Set the log level of the stream handler to warning."""
    stream_handler.setLevel(logging.WARNING)

def set_verbose() -> None:
    """Set the log level of the stream handler to debug."""
    stream_handler.setLevel(logging.DEBUG)

def get_verbosity() -> int:
    """Get the log level of the stream handler."""
    return stream_handler.level

def get_file_level() -> int:
    """Get the log level of the file handler."""
    for handler in logger.handlers:
        if isinstance(handler, TrimmedFileHandler):
            return handler.level
    return None
