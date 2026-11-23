"""Tests for which folder entries Seed.process_dats processes."""

from pathlib import Path

import pytest
from datoso.commands import seed as seed_module
from datoso.commands.seed import Seed
from datoso.repositories.dat_file import DirMultiDatFile, XMLDatFile


class FolderDat(DirMultiDatFile):
    """Directory DAT class."""


@pytest.fixture
def processed(monkeypatch, tmp_path):
    """Run process_dats and return the processed paths."""
    seen: list[Path] = []

    class RecordingProcessor:
        def __init__(self, *, seed, file, actions) -> None:  # noqa: ARG002
            seen.append(Path(file))

    monkeypatch.setattr(seed_module, 'Processor', RecordingProcessor)
    monkeypatch.setattr(seed_module, 'parse_path', lambda _path: tmp_path)
    monkeypatch.setattr(Seed, 'process_action', lambda _self, _processor: [])
    monkeypatch.setattr(Seed, 'get_prefix', lambda _self, _name: 'seed')

    def run(actions: dict, *, actions_to_execute: list | None = None) -> list[str]:
        monkeypatch.setattr(Seed, 'get_actions', lambda self: setattr(self, 'actions', actions))
        Seed(name='testseed').process_dats(actions_to_execute=actions_to_execute)
        return sorted(str(path.relative_to(tmp_path / 'seed' / 'dats')) for path in seen)

    return run


@pytest.fixture
def dats(tmp_path):
    """No-Intro-like layout with a nested Aftermarket folder."""
    root = tmp_path / 'seed' / 'dats'
    (root / 'No-Intro' / 'Aftermarket').mkdir(parents=True)
    (root / 'No-Intro' / 'A.dat').write_text('')
    (root / 'No-Intro' / 'Aftermarket' / 'B (Aftermarket).dat').write_text('')
    return root


def actions_for(*folders: str, loader: type | None) -> dict:
    load = {'action': 'LoadDatFile', **({'_class': loader} if loader else {})}
    return {f'{{dat_origin}}/{folder}': [dict(load), {'action': 'SaveToDatabase'}] for folder in folders}


def test_sub_folders_are_not_dat_files_for_file_loaders(processed, dats):  # noqa: ARG001
    paths = processed(actions_for('No-Intro', 'No-Intro/Aftermarket', loader=XMLDatFile))
    assert paths == ['No-Intro/A.dat', 'No-Intro/Aftermarket/B (Aftermarket).dat']


def test_directory_loaders_still_get_folders(processed, dats):  # noqa: ARG001
    assert 'No-Intro/Aftermarket' in processed(actions_for('No-Intro', loader=FolderDat))


def test_auto_detection_keeps_passing_folders(processed, dats):  # noqa: ARG001
    assert 'No-Intro/Aftermarket' in processed(actions_for('No-Intro', loader=None))


def test_factories_still_get_folders(processed, dats):  # noqa: ARG001
    actions = {'{dat_origin}/No-Intro': [{'action': 'LoadDatFile', '_factory': lambda _file: FolderDat}]}
    assert processed(actions) == ['No-Intro/A.dat', 'No-Intro/Aftermarket']


def test_decision_uses_the_unfiltered_actions(processed, dats):  # noqa: ARG001
    paths = processed(actions_for('No-Intro', loader=XMLDatFile), actions_to_execute=['SaveToDatabase'])
    assert paths == ['No-Intro/A.dat']


@pytest.mark.parametrize(
    ('actions', 'expected'),
    [
        ([{'action': 'LoadDatFile', '_class': XMLDatFile}], False),
        ([{'action': 'LoadDatFile', '_class': FolderDat}], True),
        ([{'action': 'LoadDatFile'}], True),
        ([{'action': 'Copy'}], True),
        ([{'action': 'LoadDatFile', '_factory': print}], True),
        ([{'action': 'LoadDatFile', '_factory': print, '_class': XMLDatFile}], True),
    ],
)
def test_loads_directories(actions, expected):
    assert Seed.loads_directories(actions) is expected
