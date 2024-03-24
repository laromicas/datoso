from datoso.repositories.dat import DatFile
from datoso.database.seeds.mia import get_mias

def mark_mias(dat_file: str):
    """ Mark a dat file as MIA. """
    dat = DatFile.from_file(dat_file=dat_file)
    dat.load()
    mias = get_mias()
    dat.mark_mias(mias)
    dat.save()