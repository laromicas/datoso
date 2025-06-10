"""Download Helper module."""
import logging
import re
import shutil
import subprocess
import urllib.request
from abc import abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from datoso.configuration import config


def downloader(url: str, destination: str, reporthook: Callable | None=None,
               *, filename_from_headers: bool=False, downloader: str | None=None) -> Path:
    """Download a file from a URL."""
    downloader = downloader or config.get('DOWNLOAD', 'PrefferDownloadUtility', fallback='urllib')
    match downloader:
        case 'wget':
            download = WgetDownload()
            return download.download(url, destination,
                                    filename_from_headers=filename_from_headers, reporthook=reporthook)
        case 'curl':
            download = CurlDownload()
            return download.download(url, destination,
                                    filename_from_headers=filename_from_headers, reporthook=reporthook)
        case 'aria2c':
            download = Aria2cDownload()
            return download.download(url, destination,
                                    filename_from_headers=filename_from_headers, reporthook=reporthook)
        case _:
            download = UrllibDownload()
            return download.download(url, destination,
                                    filename_from_headers=filename_from_headers, reporthook=reporthook)


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
            tmp_filename, headers = urllib.request.urlretrieve(url)  # noqa: S310
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
