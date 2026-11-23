"""Dedupe accepts directory DATs (a folder holding one .dat/.xml), as child or parent."""

import pytest
from datoso.repositories.dedupe import Dedupe

HEADER = '<?xml version="1.0"?>\n<datafile>\n<header><name>{name}</name><description>{name}</description></header>\n'


def rom(name: str, sha1: str) -> str:
    return f'<rom name="{name}" size="4" crc="00000000" sha1="{sha1}"/>'


def write_dat(path, name, games):
    body = ''.join(f'<game name="{game}"><description>{game}</description>{"".join(roms)}</game>\n'
                   for game, roms in games.items())
    path.write_text(HEADER.format(name=name) + body + '</datafile>\n', encoding='utf-8')
    return path


@pytest.fixture
def collection(tmp_path):
    """A TeknoParrot-like folder: one DAT where 'B' repeats a ROM of 'A'."""
    folder = tmp_path / 'TeknoParrot Collection'
    folder.mkdir()
    write_dat(folder / 'TeknoParrot Collection (2026-11-23_RomVault).dat', 'TeknoParrot Collection', {
        'A': [rom('a.bin', 'a' * 40), rom('shared.bin', 'c' * 40)],
        'B': [rom('b.bin', 'b' * 40), rom('shared.bin', 'c' * 40)],
    })
    return folder


def test_automerge_a_directory_dat(collection):
    merged = Dedupe(str(collection))
    assert merged.dedupe() == 1
    merged.save()
    text = (collection / 'TeknoParrot Collection (2026-11-23_RomVault).dat').read_text(encoding='utf-8')
    assert text.count('shared.bin') == 1


def test_directory_dat_as_parent(collection, tmp_path):
    child = write_dat(tmp_path / 'Sega ALLS.dat', 'Sega ALLS', {
        'X': [rom('shared.bin', 'c' * 40), rom('x.bin', 'd' * 40)],
    })
    assert Dedupe(str(child), str(collection)).dedupe() == 1


def test_directory_needs_exactly_one_dat(collection):
    write_dat(collection / 'other.xml', 'Other', {'O': [rom('o.bin', 'e' * 40)]})
    with pytest.raises(ValueError, match='exactly one'):
        Dedupe(str(collection))


def test_files_are_left_alone(collection):
    dat = collection / 'TeknoParrot Collection (2026-11-23_RomVault).dat'
    assert Dedupe.single_dat_in(dat) == dat
