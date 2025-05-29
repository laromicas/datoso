import unittest
from unittest import mock
import hashlib # For calculate_sha1 testing (if found later)
import os 
import shutil 
from pathlib import Path
import sys
import subprocess # For mocking Popen

# Ensure src is discoverable for imports
project_root_for_imports = Path(__file__).parent.parent.parent.parent
if str(project_root_for_imports) not in sys.path:
    sys.path.insert(0, str(project_root_for_imports))
if str(project_root_for_imports / "src") not in sys.path:
    sys.path.insert(0, str(project_root_for_imports / "src"))

from datoso.helpers.download import (
    downloader, 
    UrllibDownload, 
    WgetDownload, 
    CurlDownload, 
    Aria2cDownload
)
# calculate_sha1 is not in the current version of download.py read
# from datoso.helpers.download import calculate_sha1 

# Mock config and logging at the module level for simplicity,
# assuming they are imported as 'config' and 'logging' (or 'logger') in download.py
config_patcher = mock.patch('datoso.helpers.download.config')
logging_patcher = mock.patch('datoso.helpers.download.logging') # Used by UrllibDownload for exceptions

# The file uses 'from venv import logger' which seems incorrect.
# It should likely be 'from datoso.configuration import logger' or 'import logging; logger = logging.getLogger(...)'
# For now, assuming 'logging' is the module used for logging exceptions in UrllibDownload.
# If it's a custom logger from datoso.configuration, that would need to be patched there.


class TestDownloaderFactory(unittest.TestCase):
    def setUp(self):
        self.mock_config = config_patcher.start()
        self.mock_logging = logging_patcher.start() # For UrllibDownload's exception logging

    def tearDown(self):
        config_patcher.stop()
        logging_patcher.stop()

    @mock.patch('datoso.helpers.download.UrllibDownload')
    def test_downloader_selects_urllib_default(self, mock_UrllibDownload):
        self.mock_config.get.return_value = 'urllib' # Or fallback
        downloader("http://example.com", "dest.dat")
        mock_UrllibDownload.return_value.download.assert_called_once()

    @mock.patch('datoso.helpers.download.WgetDownload')
    def test_downloader_selects_wget(self, mock_WgetDownload):
        self.mock_config.get.return_value = 'wget'
        downloader("http://example.com", "dest.dat")
        mock_WgetDownload.return_value.download.assert_called_once()

    @mock.patch('datoso.helpers.download.CurlDownload')
    def test_downloader_selects_curl(self, mock_CurlDownload):
        self.mock_config.get.return_value = 'curl'
        downloader("http://example.com", "dest.dat")
        mock_CurlDownload.return_value.download.assert_called_once()

    @mock.patch('datoso.helpers.download.Aria2cDownload')
    def test_downloader_selects_aria2c(self, mock_Aria2cDownload):
        self.mock_config.get.return_value = 'aria2c'
        downloader("http://example.com", "dest.dat")
        mock_Aria2cDownload.return_value.download.assert_called_once()

    @mock.patch('datoso.helpers.download.UrllibDownload')
    def test_downloader_selects_unknown_falls_back_to_urllib(self, mock_UrllibDownload):
        self.mock_config.get.return_value = 'unknown_downloader' # Fallback case
        downloader("http://example.com", "dest.dat")
        mock_UrllibDownload.return_value.download.assert_called_once()


class TestUrllibDownload(unittest.TestCase):
    def setUp(self):
        # self.mock_config = config_patcher.start() # Not directly used by UrllibDownload class itself
        self.mock_logging = logging_patcher.start() 

    def tearDown(self):
        # config_patcher.stop()
        logging_patcher.stop()

    @mock.patch('datoso.helpers.download.urllib.request.urlretrieve')
    def test_urllib_download_simple(self, mock_urlretrieve):
        downloader_instance = UrllibDownload()
        url = "http://example.com/file.dat"
        destination = "local/file.dat"
        mock_reporthook = mock.Mock()
        
        result = downloader_instance.download(url, destination, reporthook=mock_reporthook)
        
        self.assertEqual(result, destination)
        mock_urlretrieve.assert_called_once_with(url, destination, reporthook=mock_reporthook)

    def test_urllib_download_invalid_url_scheme(self):
        downloader_instance = UrllibDownload()
        with self.assertRaises(ValueError) as context:
            downloader_instance.download("ftp://example.com/file.dat", "local/file.dat")
        self.assertIn('URL must start with "http:" or "https:"', str(context.exception))

    @mock.patch('datoso.helpers.download.urllib.request.urlretrieve')
    @mock.patch('datoso.helpers.download.shutil.move')
    @mock.patch('datoso.helpers.download.Path')
    def test_urllib_download_with_filename_from_headers(self, mock_Path, mock_shutil_move, mock_urlretrieve):
        downloader_instance = UrllibDownload()
        url = "http://example.com/download"
        destination_dir_str = "local_dir"
        
        mock_headers = mock.Mock()
        mock_headers.get_filename.return_value = "header_filename.dat"
        mock_urlretrieve.return_value = ("/tmp/tmpfile", mock_headers) # Simulate (tmp_filename, headers)
        
        # Mock Path interactions
        mock_dest_path_obj = mock.MagicMock(spec=Path)
        mock_Path.return_value = mock_dest_path_obj # Path(destination_dir_str) returns this
        mock_final_path_obj = mock.MagicMock(spec=Path)
        mock_dest_path_obj.__truediv__.return_value = mock_final_path_obj # Path(dest) / headers.get_filename()
        
        result = downloader_instance.download(url, destination_dir_str, filename_from_headers=True)
        
        self.assertEqual(result, mock_final_path_obj)
        mock_urlretrieve.assert_called_once_with(url)
        mock_shutil_move.assert_called_once_with("/tmp/tmpfile", mock_final_path_obj)
        mock_Path.assert_called_once_with(destination_dir_str)
        mock_dest_path_obj.__truediv__.assert_called_once_with("header_filename.dat")


    @mock.patch('datoso.helpers.download.urllib.request.urlretrieve', side_effect=TypeError("Mocked TypeError"))
    def test_urllib_download_type_error_handling(self, mock_urlretrieve):
        downloader_instance = UrllibDownload()
        url = "http://example.com/download_type_error"
        
        result = downloader_instance.download(url, "local_dir", filename_from_headers=True)
        
        self.assertIsNone(result)
        self.mock_logging.exception.assert_any_call('Error downloading %s', url)


    @mock.patch('datoso.helpers.download.urllib.request.urlretrieve', side_effect=Exception("Mocked General Exception"))
    def test_urllib_download_general_exception_handling(self, mock_urlretrieve):
        downloader_instance = UrllibDownload()
        url = "http://example.com/download_general_error"
        
        result = downloader_instance.download(url, "local_dir", filename_from_headers=True)
        
        self.assertIsNone(result)
        self.mock_logging.exception.assert_any_call('Error downloading %s', url)


class TestPopenDownloadBase(unittest.TestCase):
    def setUp(self):
        self.popen_patcher = mock.patch('datoso.helpers.download.Download.popen') # Patch on base class
        self.mock_popen = self.popen_patcher.start()
        # self.mock_config = config_patcher.start() # Not directly used by these classes
        # self.mock_logging = logging_patcher.start()

    def tearDown(self):
        self.popen_patcher.stop()
        # config_patcher.stop()
        # logging_patcher.stop()

class TestWgetDownload(TestPopenDownloadBase):
    def test_wget_download_simple(self):
        downloader_instance = WgetDownload()
        url = "http://example.com/file.zip"
        destination = "local/file.zip"
        self.mock_popen.return_value = ("stdout", "stderr") # Simulate Popen result

        result = downloader_instance.download(url, destination)
        
        self.assertEqual(result, destination)
        expected_args = ['wget', url, '-O', destination]
        self.mock_popen.assert_called_once_with(expected_args)

    def test_wget_download_filename_from_headers(self):
        downloader_instance = WgetDownload()
        url = "http://example.com/download"
        destination_dir = "downloads_wget"
        # Simulate stderr output from wget that contains the filename
        # Example: 'Saved L‘”local/real_filename.ext”’'
        # Example from code: – ‘/tmp/file.dat’ saved [12345/12345] -> "file.dat"
        # Example: Remote file name is ‘file.zip’. -> "file.zip"
        # Example: ‘logo.png’ saved [16K] -> "logo.png"
        # Example: Saving to: ‘/tmp/datutils.tar.gz’ -> "/tmp/datutils.tar.gz"
        # The regex `r'"([^"]*)"'` implies it expects quotes like: Saved to: "filename.ext"
        mock_stderr = 'stderr output with Saved to: "actual_filename.zip"'
        self.mock_popen.return_value = ("stdout", mock_stderr)
        
        expected_final_path = Path(destination_dir) / "actual_filename.zip"
        
        result = downloader_instance.download(url, destination_dir, filename_from_headers=True)
        
        self.assertEqual(result, expected_final_path)
        expected_args = ['wget', url, '--content-disposition', '--trust-server-names', '-nv']
        self.mock_popen.assert_called_once_with(expected_args, cwd=destination_dir)

    def test_wget_parse_filename(self):
        downloader_instance = WgetDownload()
        # Test cases from original code examples or typical wget outputs
        self.assertEqual(downloader_instance.parse_filename('Saved to: "file.dat"'), "file.dat")
        self.assertEqual(downloader_instance.parse_filename('Remote file name is "file.zip".'), "file.zip")
        self.assertEqual(downloader_instance.parse_filename('‘logo.png’ saved [16K]'), "logo.png") # Original code implies this works
        self.assertEqual(downloader_instance.parse_filename('Saving to: ‘/tmp/datutils.tar.gz’'), "/tmp/datutils.tar.gz")


class TestCurlDownload(TestPopenDownloadBase):
    def test_curl_download_simple(self):
        downloader_instance = CurlDownload()
        url = "http://example.com/file.img"
        destination = "local/file.img"
        self.mock_popen.return_value = ("stdout", "stderr")

        result = downloader_instance.download(url, destination)

        self.assertEqual(result, destination)
        expected_args = ['curl', '-L', url, '-o', destination, '-J', '-L', '-k', '-s']
        self.mock_popen.assert_called_once_with(expected_args)

    def test_curl_download_filename_from_headers_success(self):
        downloader_instance = CurlDownload()
        url = "http://example.com/getfile"
        destination_dir = "downloads_curl"
        # Curl with -JLO might output something like:
        # curl: Saved to filename 'downloaded_file.tar.gz'
        mock_stdout = "curl: Saved to filename 'header_file.tar.gz'"
        self.mock_popen.return_value = (mock_stdout, "stderr")

        expected_final_path = Path(destination_dir) / "header_file.tar.gz"
        result = downloader_instance.download(url, destination_dir, filename_from_headers=True)

        self.assertEqual(result, expected_final_path)
        expected_args = ['curl', '-JLOk', url]
        self.mock_popen.assert_called_once_with(expected_args, cwd=destination_dir)
        
    def test_curl_download_filename_from_headers_error(self):
        downloader_instance = CurlDownload()
        url = "http://example.com/getfile_error"
        destination_dir = "downloads_curl_error"
        self.mock_popen.return_value = ("", "stderr_indicating_error") # Empty stdout indicates error

        with self.assertRaises(ValueError) as context:
            downloader_instance.download(url, destination_dir, filename_from_headers=True)
        self.assertIn(f'Error downloading file from {url}', str(context.exception))


class TestAria2cDownload(TestPopenDownloadBase):
    def test_aria2c_download_simple(self):
        downloader_instance = Aria2cDownload()
        url = "http://example.com/archive.7z"
        destination_str = "local_folder/archive.7z"
        destination_path = Path(destination_str)
        
        self.mock_popen.return_value = ("stdout", "stderr")

        result = downloader_instance.download(url, destination_str)
        self.assertEqual(result, destination_str) # Returns string path
        expected_args = ['aria2c', '-x', '16', url, '-o', destination_path.name]
        self.mock_popen.assert_called_once_with(expected_args, cwd=destination_path.parent)

    def test_aria2c_download_filename_from_headers(self):
        downloader_instance = Aria2cDownload()
        url = "http://example.com/get_archive"
        destination_dir = "downloads_aria2c"
        # Aria2c output for --content-disposition might be complex,
        # The parse_filename method uses: output[output.rfind('/')+1:].strip()
        # This implies it expects a path-like string in stdout.
        # Example: "Download complete: /tmp/downloads_aria2c/actual_filename.rar"
        # Or just "actual_filename.rar" if aria2c saves it directly with that name from header.
        # Let's assume the output contains the filename.
        mock_stdout = "Some output line\nDownload results:\n* /path/to/downloaded/actual_file.rar\nMore output"
        self.mock_popen.return_value = (mock_stdout, "stderr")
        
        expected_final_path = Path(destination_dir) / "actual_file.rar"
        result = downloader_instance.download(url, destination_dir, filename_from_headers=True)

        self.assertEqual(result, expected_final_path)
        expected_args = ['aria2c', '-x', '16', url, '--content-disposition', 
                         '--download-result=hide', '--summary-interval=0']
        self.mock_popen.assert_called_once_with(expected_args, cwd=destination_dir)

    def test_aria2c_parse_filename(self):
        downloader_instance = Aria2cDownload()
        self.assertEqual(downloader_instance.parse_filename("path/to/filename.ext"), "filename.ext")
        self.assertEqual(downloader_instance.parse_filename("filename.ext"), "filename.ext")
        self.assertEqual(downloader_instance.parse_filename("  filename.ext  "), "filename.ext")
        self.assertEqual(downloader_instance.parse_filename(""), "")


# calculate_sha1 function is not in the provided download.py content.
# If it were, tests would be like:
# class TestCalculateSha1(unittest.TestCase):
#     @mock.patch('builtins.open', new_callable=mock.mock_open, read_data=b'test data')
#     def test_calculate_sha1_correct(self, mock_file_open):
#         expected_sha1 = hashlib.sha1(b'test data').hexdigest()
#         actual_sha1 = calculate_sha1("dummy_path.dat")
#         self.assertEqual(actual_sha1, expected_sha1)
#         mock_file_open.assert_called_once_with("dummy_path.dat", 'rb')


if __name__ == '__main__':
    unittest.main()
