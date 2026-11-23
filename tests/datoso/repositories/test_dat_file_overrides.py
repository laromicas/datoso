"""System rules (overrides/extra_configs) apply to every DatFile type, including directory DATs."""

from types import SimpleNamespace

import pytest
from datoso.repositories import dat_file
from datoso.repositories.dat_file import ClrMameProDatFile, DirMultiDatFile, XMLDatFile


class FolderDat(DirMultiDatFile):
    """Directory DAT, like eggman's TeknoparrotDat."""

    seed = 'eggman'


@pytest.fixture
def rule(monkeypatch):
    """Make System.load() find the given rule."""
    found = {}

    class FakeSystem(SimpleNamespace):
        def load(self) -> None:
            self.__dict__.update(found)

    monkeypatch.setattr(dat_file, 'System', FakeSystem)
    return found


@pytest.mark.parametrize('cls', [FolderDat, XMLDatFile, ClrMameProDatFile])
def test_overrides_on_every_dat_type(rule, cls):
    rule.update(system_type='Arcade', override={'system': 'TeknoParrot', 'company': None})
    dat = cls(name='TeknoParrot Collection', system='TeknoParrot Collection')
    found = dat.overrides()
    assert (found.system, dat.system, dat.system_type) == ('TeknoParrot Collection', 'TeknoParrot', 'Arcade')


def test_extra_configs_on_directory_dat(rule):
    rule.update(system_type='Arcade', extra_configs={'empty_suffix': {'eggman': 'DataCollective'}})
    dat = FolderDat(name='Sega ALLS', system='Sega ALLS')
    dat.extra_configs(dat.overrides())
    assert dat.suffix == 'DataCollective'


def test_no_rule_leaves_the_dat_alone(rule):  # noqa: ARG001
    dat = FolderDat(name='TeknoParrot Supplementary', system='TeknoParrot Supplementary')
    dat.extra_configs(dat.overrides())
    assert (dat.system, dat.system_type, dat.suffix) == ('TeknoParrot Supplementary', None, None)
