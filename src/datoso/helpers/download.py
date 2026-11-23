"""Download Helper module."""
import logging
import re
import shutil
import subprocess
import urllib.request
from abc import abstractmethod
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Thread
from typing import Self, TextIO
from urllib.parse import unquote, urlparse

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.text import Text

from datoso.configuration import config
from datoso.configuration.logger import stream_handler


def downloader(url: str, destination: str, reporthook: Callable | None=None,  # noqa: PLR0913
               *, filename_from_headers: bool=False, downloader: str | None=None,
               progress: 'DownloadProgress | None' = None) -> Path:
    """Download a file from a URL, with a progress bar if ``progress`` is given."""
    downloader = downloader or config.get('DOWNLOAD', 'PrefferDownloadUtility', fallback='urllib')
    match downloader:
        case 'wget':
            download = WgetDownload()
        case 'curl':
            download = CurlDownload()
        case 'aria2c':
            download = Aria2cDownload()
        case _:
            download = UrllibDownload()
    if progress is None:
        return download.download(url, destination, filename_from_headers=filename_from_headers, reporthook=reporthook)
    name = url_label(url) if filename_from_headers else Path(destination).name
    # Poll the file for wget/curl; aria2c preallocates it, so its size means nothing.
    watch = None if filename_from_headers or not isinstance(download, WgetDownload | CurlDownload) else destination
    with progress.file(name, watch=watch) as task:
        hook = progress.reporthook(task) if isinstance(download, UrllibDownload) else None
        return download.download(url, destination, filename_from_headers=filename_from_headers, reporthook=hook)


def url_label(url: str) -> str:
    """Last two path parts of a URL ('http://x/datfile/psx/' -> 'datfile/psx')."""
    parts = [part for part in unquote(urlparse(url).path).split('/') if part]
    return '/'.join(parts[-2:]) or url


class AmountColumn(DownloadColumn):
    """Bytes for file bars, done/total for the overall bar."""

    def render(self, task) -> Text:  # noqa: ANN001
        """Render the column."""
        if task.fields.get('file'):
            return super().render(task)
        return Text(f'{int(task.completed)}/{int(task.total)}' if task.total else '', style='progress.download')


class SpeedColumn(TransferSpeedColumn):
    """Speed, only for file bars."""

    def render(self, task) -> Text:  # noqa: ANN001
        """Render the column."""
        return super().render(task) if task.fields.get('file') else Text('')


class _ConsoleStream:
    """Prints log lines above the live bars."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def write(self, text: str) -> None:
        if text.strip():
            self.console.print(Text.from_ansi(text.rstrip('\n')), soft_wrap=True)

    def flush(self) -> None:
        pass


class DownloadProgress:
    """Thread-safe rich progress: an overall bar plus one bar per active download. Hidden when quiet.

    Usage::

        with DownloadProgress(total=len(urls)) as progress:
            executor.map(lambda url: downloader(url, dest, progress=progress), urls)
    """

    def __init__(self, total: int | None = None, description: str = 'Downloading') -> None:  # noqa: D107
        self.progress = Progress(
            TextColumn('{task.description}'), BarColumn(), TaskProgressColumn(), AmountColumn(), SpeedColumn(),
            TimeRemainingColumn(),
            disable=config.getboolean('COMMAND', 'Quiet', fallback=False),
        )
        # With one file there is no overall bar, so its own bar stays when done.
        self.keep_files = not total or total <= 1
        self.overall = self.progress.add_task(description, total=total, visible=not self.keep_files)
        self._log_stream = None

    def __enter__(self) -> Self:  # noqa: D105
        self.progress.start()
        if not self.progress.disable:
            self._log_stream = stream_handler.setStream(_ConsoleStream(self.progress.console))
        return self

    def __exit__(self, *exc: object) -> None:  # noqa: D105
        if self._log_stream is not None:
            stream_handler.setStream(self._log_stream)
            self._log_stream = None
        self.progress.stop()

    def advance(self) -> None:
        """Count one item as done on the overall bar (``downloader`` does this itself)."""
        self.progress.advance(self.overall)

    def reporthook(self, task: TaskID) -> Callable[[int, int, int], None]:
        """Return a urlretrieve reporthook that updates ``task``."""
        def report(block_num: int, block_size: int, total_size: int) -> None:
            total = total_size if total_size > 0 else None
            done = block_num * block_size
            self.progress.update(task, completed=min(done, total) if total else done, total=total)
        return report

    @contextmanager
    def file(self, name: str, total: int | None = None, watch: str | Path | None = None) -> Iterator[TaskID]:
        """Show a bar for one download; ``watch`` follows that file's size on disk."""
        task = self.progress.add_task(name, total=total, file=True)
        done = Event()

        def follow() -> None:
            path = Path(watch)
            while not done.wait(0.5):
                self.progress.update(task, completed=path.stat().st_size if path.exists() else 0)

        watcher = Thread(target=follow, daemon=True) if watch else None
        if watcher:
            watcher.start()
        try:
            yield task
        finally:
            done.set()
            if watcher:
                watcher.join()
            current = next(item for item in self.progress.tasks if item.id == task)
            size = Path(watch).stat().st_size if watch and Path(watch).exists() else current.total or current.completed
            self.progress.update(task, total=size or 1, completed=size or 1)
            if not self.keep_files:
                self.progress.remove_task(task)
            self.advance()


class Download:
    """Download class."""

    @abstractmethod
    def download(self, url: str, destination: str, *,
                 reporthook: Callable | None=None, filename_from_headers: bool=False) -> Path:
        """Download a file."""

    def popen(self, args: str | list, cwd: str | None=None, *, text: bool=True,
              stdout: Path | TextIO = subprocess.PIPE, stderr: Path | TextIO=subprocess.PIPE) -> tuple:
        """Execute a command."""
        pipes = subprocess.Popen(args, cwd=cwd, text=text, stdout=stdout, stderr=stderr)  # noqa: S603
        std_out, std_err = pipes.communicate()
        return std_out, std_err


class UrllibDownload(Download):
    """Urllib Download class."""

    def download(self, url: str, destination: str, *,
                 reporthook: Callable | None=None, filename_from_headers: bool=False) -> Path:
        """Download a file."""
        if not url.startswith(('http:', 'https:')):
            msg = 'URL must start with "http:" or "https:"'
            raise ValueError(msg)

        if not filename_from_headers:
            urllib.request.urlretrieve(url, destination, reporthook=reporthook)  # noqa: S310
            return destination
        headers = None
        try:
            tmp_filename, headers = urllib.request.urlretrieve(url, reporthook=reporthook)  # noqa: S310
            local_filename = Path(destination) / headers.get_filename()
            shutil.move(tmp_filename, local_filename)
        except TypeError:
            logging.exception('Error downloading %s', url)
            logging.exception('Headers: %s', headers)
            return None
        except Exception:
            logging.exception('Error downloading %s', url)
            logging.exception('Headers: %s', headers)
            return None
        return local_filename


class WgetDownload(Download):
    """Wget Download class."""

    def download(self, url: str, destination: str, *,
                 reporthook: Callable | None=None, filename_from_headers: bool=False) -> Path:  # noqa: ARG002
        """Download a file."""
        # TODO(laromicas): Add reporthook
        if filename_from_headers:
            args = ['wget', url, '--content-disposition', '--trust-server-names', '-nv']
            std_out, std_err = self.popen(args, cwd=destination)
            return Path(destination) / self.parse_filename(std_err)
        args = ['wget', url, '-O', destination]
        std_out, std_err = self.popen(args)
        return destination

    def parse_filename(self, output: str) -> str:
        """Parse the filename from the output."""
        my_list = [
            match for group in re.findall(r"(?:'([^']*)'|\"([^\"]*)\"|‘([^’]*)’)", output)  # noqa: RUF001
            for match in group if match
        ]
        return my_list[-1]


class CurlDownload(Download):
    """Curl Download class."""

    def download(self, url: str, destination: str, *,
                 reporthook: Callable | None=None, filename_from_headers: bool=False) -> Path:  # noqa: ARG002
        """Download a file."""
        # TODO(laromicas): Add reporthook
        if filename_from_headers:
            args = ['curl', '-JLOk', url]
            std_out, _ = self.popen(args, cwd=destination)
            if not std_out:
                msg = f'Error downloading file from {url} {std_out}'
                raise ValueError(msg)
            return Path(destination) / self.parse_filename(std_out)
        args = ['curl', '-L', url, '-o', destination, '-J', '-L', '-k', '-s']
        std_out, _ = self.popen(args)
        return destination

    def parse_filename(self, output: str) -> str:
        """Parse the filename from the output."""
        my_list = [
            match for group in re.findall(r"(?:'([^']*)'|\"([^\"]*)\"|‘([^’]*)’)", output)  # noqa: RUF001
            for match in group if match
        ]
        return my_list[-1]


class Aria2cDownload(Download):
    """Aria2c Download class."""

    def download(self, url: str, destination: str, *,
                 reporthook: Callable | None=None, filename_from_headers: bool=False) -> Path:  # noqa: ARG002
        """Download a file."""
        # TODO(laromicas): Add reporthook
        if filename_from_headers:
            args = ['aria2c', '-x', '16', url, '--content-disposition',
                    '--download-result=hide', '--summary-interval=0']
            std_out, std_err = self.popen(args, cwd=destination)
            return Path(destination) / self.parse_filename(std_out)
        folder = Path(destination).parent
        file = Path(destination).name
        args = ['aria2c', '-x', '16', url, '-o', file]
        std_out, std_err = self.popen(args, cwd=folder)
        return destination

    def parse_filename(self, output: str) -> str:
        """Parse the filename from the output."""
        return output[output.rfind('/')+1:].strip()
