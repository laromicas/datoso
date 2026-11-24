"""Dedupe accepts directory DATs (every .dat/.xml in the folder tree), as child or parent."""

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


def test_automerge_every_dat_recursively(collection):
    nested = collection / 'Sub' / 'Deeper'
    nested.mkdir(parents=True)
    other = write_dat(nested / 'other.xml', 'Other', {
        'O': [rom('o.bin', 'e' * 40)], 'P': [rom('o.bin', 'e' * 40), rom('p.bin', 'f' * 40)],
    })
    untouched = write_dat(collection / 'Sub' / 'clean.dat', 'Clean', {'C': [rom('c.bin', '1' * 40)]})
    before = untouched.stat().st_mtime_ns
    merged = Dedupe(str(collection))
    assert merged.dedupe() == 2  # one in each DAT that has duplicates, each deduped on its own
    merged.save()
    assert other.read_text(encoding='utf-8').count('o.bin') == 1
    assert untouched.stat().st_mtime_ns == before  # unchanged DATs are not rewritten


def test_directory_parent_counts_all_its_dats(collection, tmp_path):
    write_dat(collection / 'more.xml', 'More', {'M': [rom('m.bin', 'd' * 40)]})
    child = write_dat(tmp_path / 'Sega ALLS.dat', 'Sega ALLS', {
        'X': [rom('shared.bin', 'c' * 40), rom('m.bin', 'd' * 40), rom('x.bin', '9' * 40)],
    })
    assert Dedupe(str(child), str(collection)).dedupe() == 2


def test_output_file_needs_a_single_dat(collection):
    write_dat(collection / 'more.xml', 'More', {'M': [rom('m.bin', 'd' * 40)]})
    merged = Dedupe(str(collection))
    merged.dedupe()
    with pytest.raises(ValueError, match='single DAT'):
        merged.save('out.dat')


def test_files_are_left_alone(collection):
    dat = collection / 'TeknoParrot Collection (2026-11-23_RomVault).dat'
    assert Dedupe.dats_in(dat) == [dat]
