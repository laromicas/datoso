"""Mark a dat file as MIA."""
from datoso.database.seeds.mia import get_mias
from datoso.repositories.dat_file import DatFile


def mark_mias(dat_file: str) -> None:
    """Mark a dat file as MIA."""
    dat = DatFile.from_file(file=dat_file)
    dat.load()
    mias = get_mias()
    dat.mark_mias(mias)
    dat.save()
