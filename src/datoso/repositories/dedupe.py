import logging
from datoso.database.models.datfile import Dat
from datoso.repositories.dat import DatFile, XMLDatFile, ClrMameProDatFile

class Dedupe:
    """ Merge two dat files. """

    child = {}
    parent = {}

    def __init__(self, child, parent=None):
        self.child = {}
        self.parent = {}

        def load_metadata(var, obj):
            if isinstance(var, str):
                if ':' in var:
                    splitted = var.split(':')
                    seed = splitted[0]
                    name = splitted[1]
                    obj['db'] = Dat(name=name, seed=seed)
                    obj['db'].load()
                    var = obj['db']
                elif var.endswith(('.dat', '.xml')):
                    obj['file'] = var
                else:
                    raise Exception("Invalid dat file")
            if isinstance(var, Dat):
                obj['db'] = var
                obj['file'] = getattr(var, 'new_file', None) or var.file
            if isinstance(var, DatFile):
                obj['dat'] = var
            else:
                obj['dat'] = self.get_dat_file(obj['file'])

        load_metadata(child, self.child)
        if not parent:
            parent = self.child['db'].parent
            load_metadata(parent, self.parent)

    def get_dat_file(self, file):
        try:
            dat = XMLDatFile(file=file)
            dat.load()
            return dat
        except Exception:
            pass
        try:
            dat = ClrMameProDatFile(file=file)
            dat.load()
            return dat
        except Exception:
            pass
        raise Exception("Invalid dat file")

    def dedupe(self):
        if self.parent:
            self.child['dat'].merge_with(self.parent['dat'])
        else:
            self.child['dat'].dedupe()
        logging.info("Deduped %i roms", len(self.child['dat'].merged_roms))
        return self.child['dat']

    def save(self, file=None):
        if file:
            self.child['dat'].file = file
        self.child['dat'].save()