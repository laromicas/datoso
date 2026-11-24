"""Tests for download progress bars, including parallel downloads."""

import functools
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import pytest
from datoso.configuration import config
from datoso.configuration.logger import stream_handler
from datoso.helpers import download as download_module
from datoso.helpers.download import DownloadProgress, content_length, downloader, url_label


@pytest.fixture
def server(tmp_path):
    """Serve tmp_path/www over local HTTP."""
    www = tmp_path / 'www'
    www.mkdir()
    for name in ('a.dat', 'b.dat', 'c.dat'):
        (www / name).write_bytes(name.encode() * 5000)
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(www))
    handler.log_message = lambda *_args: None
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{httpd.server_port}', www
    httpd.shutdown()


@pytest.fixture(autouse=True)
def urllib_not_quiet(monkeypatch):
    monkeypatch.setitem(config['DOWNLOAD'], 'PrefferDownloadUtility', 'urllib')
    monkeypatch.setitem(config['COMMAND'], 'Quiet', 'false')


def test_url_label():
    assert url_label('http://redump.org/datfile/psx/') == 'datfile/psx'
    assert url_label('http://x.org/a%20b.zip') == 'a b.zip'


def test_parallel_downloads_share_one_progress(server, tmp_path):
    url, www = server
    out = tmp_path / 'out'
    out.mkdir()
    names = ['a.dat', 'b.dat', 'c.dat']
    with DownloadProgress(total=3) as progress, ThreadPoolExecutor(max_workers=3) as executor:
        list(executor.map(lambda name: downloader(f'{url}/{name}', out / name, progress=progress), names))
        overall = progress.progress.tasks[0]
        assert (overall.completed, overall.total, overall.visible) == (3, 3, True)
        assert len(progress.progress.tasks) == 1  # finished file bars are removed
    for name in names:
        assert (out / name).read_bytes() == (www / name).read_bytes()


def test_single_download_keeps_its_bar(server, tmp_path):
    url, _ = server
    with DownloadProgress(total=1) as progress:
        downloader(f'{url}/a.dat', tmp_path / 'a.dat', progress=progress)
        overall, file = progress.progress.tasks
        assert not overall.visible
        assert (file.description, file.completed, file.total) == ('a.dat', 25000, 25000)


def test_subprocess_downloads_follow_the_file(tmp_path):
    target = tmp_path / 'x.zip'

    def fake_wget(_self, _url, destination, **_kw):
        destination.write_bytes(b'0' * 1234)
        return destination

    with mock.patch.object(download_module.WgetDownload, 'download', fake_wget), \
            mock.patch.object(download_module, 'content_length', return_value=1234) as head, \
            DownloadProgress() as progress:
        downloader('http://example.org/x.zip', target, downloader='wget', progress=progress)
        file = progress.progress.tasks[1]
        assert (file.completed, file.total, file.finished) == (1234, 1234, True)
    head.assert_called_once_with('http://example.org/x.zip')


def test_content_length(server):
    url, _ = server
    assert content_length(f'{url}/a.dat') == 25000
    assert content_length(f'{url}/missing.dat') is None
    assert content_length('ftp://example.org/x') is None


def test_hidden_when_quiet(monkeypatch):
    monkeypatch.setitem(config['COMMAND'], 'Quiet', 'true')
    with DownloadProgress(total=2) as progress:
        assert progress.progress.disable
        assert not isinstance(stream_handler.stream, download_module._ConsoleStream)  # noqa: SLF001


def test_log_lines_go_above_the_bars_while_live():
    original = stream_handler.stream
    with DownloadProgress(total=2) as progress, mock.patch.object(progress.progress.console, 'print') as printed:
        logging.getLogger('somewhere').warning('hello')
        assert printed.call_args.args[0].plain == 'hello'
    assert stream_handler.stream is original
