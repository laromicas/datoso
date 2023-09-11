from abc import abstractmethod
import os
import re
import shutil
import subprocess
import urllib.request
import logging
from datoso.configuration import config

def downloader(url, destination, reporthook=None, filename_from_headers=False):
    match config.get('DOWNLOAD', 'PrefferDownloadUtility', fallback='urllib'):
        case 'wget':
            download = WgetDownload()
            return download.download(url, destination, reporthook=reporthook, filename_from_headers=filename_from_headers)
        case 'curl':
            download = CurlDownload()
            return download.download(url, destination, reporthook=reporthook, filename_from_headers=filename_from_headers)
        case 'aria2c':
            download = Aria2cDownload()
            return download.download(url, destination, reporthook=reporthook, filename_from_headers=filename_from_headers)
        case _:
            download = UrllibDownload()
            return download.download(url, destination, reporthook=reporthook, filename_from_headers=filename_from_headers)

class Download:
    @abstractmethod
    def download(self, url, destination, reporthook=None, filename_from_headers=False):
        pass

    def popen(self, args, cwd=None, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        pipes = subprocess.Popen(args, cwd=cwd, text=text, stdout=stdout, stderr=stderr)
        std_out, std_err = pipes.communicate()
        return std_out, std_err

class UrllibDownload(Download):
    def download(self, url, destination, reporthook=None, filename_from_headers=False):
        if not filename_from_headers:
            urllib.request.urlretrieve(url, destination, reporthook=reporthook)
            return destination
        else:
            try:
                tmp_filename, headers = urllib.request.urlretrieve(url)
                local_filename = os.path.join(destination, headers.get_filename())
                shutil.move(tmp_filename, local_filename)
            except Exception as e:
                logging.error(f'Error downloading {url}: {e}')
                return
            return local_filename

class WgetDownload(Download):
    def download(self, url, destination, reporthook=None, filename_from_headers=False):
        if filename_from_headers:
            args = ['wget', url, '--content-disposition', '--trust-server-names', '-nv']
            std_out, std_err = self.popen(args, cwd=destination)
            return os.path.join(destination, self.parse_filename(std_err))
        else:
            args = ['wget', url, '-O', destination]
            std_out, std_err = self.popen(args)
        return destination

    def parse_filename(self, output):
        my_list = re.findall(r'"([^"]*)"', output)
        return my_list[-1]

class CurlDownload(Download):
    def download(self, url, destination, reporthook=None, filename_from_headers=False):
        if filename_from_headers:
            # args = ['curl', '-L', url, '-o', destination, '-J', '-L', '-k', '-s']
            args = ['curl', '-JLOk', url]
            std_out, std_err = self.popen(args, cwd=destination)
            return os.path.join(destination, self.parse_filename(std_out))
        else:
            args = ['curl', '-L', url, '-o', destination, '-J', '-L', '-k', '-s']
            std_out, std_err = self.popen(args)
            return destination

    def parse_filename(self, output):
        my_list = re.findall(r"'([^']*)'", output)
        return my_list[-1]

class Aria2cDownload(Download):
    def download(self, url, destination, reporthook=None, filename_from_headers=False):
        if filename_from_headers:
            args = ['aria2c', '-x', '16', url, '--content-disposition', '--download-result=hide', '--summary-interval=0']
            std_out, std_err = self.popen(args, cwd=destination)
            return os.path.join(destination, self.parse_filename(std_out))
        else:
            dir = os.path.dirname(destination)
            file = os.path.basename(destination)
            args = ['aria2c', '-x', '16', url, '-o', file]
            std_out, std_err = self.popen(args, cwd=dir)
            return destination

    def parse_filename(self, output):
        return output[output.rfind('/')+1:].strip()
