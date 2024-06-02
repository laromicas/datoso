import logging
import re
import shutil
import subprocess
import urllib.request
from abc import abstractmethod
from pathlib import Path

from datoso.configuration import config


def downloader(url, destination, reporthook=None, filename_from_headers=None):
    match config.get('DOWNLOAD', 'PrefferDownloadUtility', fallback='urllib'):
        case 'wget':
            download = WgetDownload()
            return download.download(url, destination,filename_from_headers=filename_from_headers or False,
                reporthook=reporthook)
        case 'curl':
            download = CurlDownload()
            return download.download(url, destination,filename_from_headers=filename_from_headers or False,
                reporthook=reporthook)
        case 'aria2c':
            download = Aria2cDownload()
            return download.download(url, destination,filename_from_headers=filename_from_headers or False,
                reporthook=reporthook)
        case _:
            download = UrllibDownload()
            return download.download(url, destination,filename_from_headers=filename_from_headers or False,
                reporthook=reporthook)


class Download:
    @abstractmethod
    def download(self, url, destination, filename_from_headers=None, reporthook=None):
        pass

    def popen(self, args, cwd=None, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE): # noqa: PLR0913
        pipes = subprocess.Popen(args, cwd=cwd, text=text, stdout=stdout, stderr=stderr)
        std_out, std_err = pipes.communicate()
        return std_out, std_err


class UrllibDownload(Download):
    def download(self, url, destination, filename_from_headers=None, reporthook=None):
        if not url.startswith(('http:', 'https:')):
            msg = 'URL must start with "http:" or "https:"'
            raise ValueError(msg)

        if not filename_from_headers:
            urllib.request.urlretrieve(url, destination, reporthook=reporthook)  # noqa: S310
            return destination
        try:
            tmp_filename, headers = urllib.request.urlretrieve(url)  # noqa: S310
            local_filename = Path(destination) / headers.get_filename()
            shutil.move(tmp_filename, local_filename)
        except Exception:
            logging.exception('Error downloading %s', url)
            return None
        return local_filename


class WgetDownload(Download):
    def download(self, url, destination, filename_from_headers=None, reporthook=None): # noqa: ARG002
        # TODO(laromicas): Add reporthook
        if filename_from_headers:
            args = ['wget', url, '--content-disposition', '--trust-server-names', '-nv']
            std_out, std_err = self.popen(args, cwd=destination)
            return Path(destination) / self.parse_filename(std_err)
        args = ['wget', url, '-O', destination]
        std_out, std_err = self.popen(args)
        return destination

    def parse_filename(self, output):
        my_list = re.findall(r'"([^"]*)"', output)
        return my_list[-1]


class CurlDownload(Download):
    def download(self, url, destination, filename_from_headers=None, reporthook=None): # noqa: ARG002
        # TODO(laromicas): Add reporthook
        if filename_from_headers:
            args = ['curl', '-JLOk', url]
            std_out, _ = self.popen(args, cwd=destination)
            return Path(destination) / self.parse_filename(std_out)
        args = ['curl', '-L', url, '-o', destination, '-J', '-L', '-k', '-s']
        std_out, _ = self.popen(args)
        return destination

    def parse_filename(self, output):
        my_list = re.findall(r"'([^']*)'", output)
        return my_list[-1]


class Aria2cDownload(Download):
    def download(self, url, destination, filename_from_headers=None, reporthook=None): # noqa: ARG002
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

    def parse_filename(self, output):
        return output[output.rfind('/')+1:].strip()
