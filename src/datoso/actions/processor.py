"""
Process actions.
"""
# pylint: disable=too-few-public-methods
import os
import shutil
from datoso.configuration import config
from datoso.repositories.dedupe import Dedupe
from datoso.database.models.datfile import Dat

class Processor:
    """ Process actions. """
    _previous = None
    actions = []
    seed = None
    file = None

    def __init__(self, **kwargs):
        self._previous = None
        self.__dict__.update(kwargs)

    def process(self):
        """ Process actions. """
        for action in self.actions:
            action_class = globals()[action['action']](file=self.file, seed=self.seed, previous=self._previous, **action)
            yield action_class.process()
            self._previous = action_class.output


class Process:
    """ Process Base class. """
    output = None
    status = None
    previous = {}
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class LoadDatFile(Process):
    """ Load a dat file. """
    # pylint: disable=no-member
    class_name = None
    file = None
    seed = None
    database = None
    _class = None
    _factory = None
    _dat = None

    def process(self):
        """ Load a dat file. """
        from datoso.database.models.datfile import Dat
        # if getattr(self, 'factory', None) and self.factory:
        #     self._factory = locate(self.factory)
        #     self._class = self._factory(self.file)
        # else:
        #     self._class = locate(self.class_obj)
        # self._class = locate(self.class_obj)
        self._dat = self._class(file=self.file)
        self._dat.load()
        self.database = Dat(seed=self.seed, **self._dat.dict())
        self.output = self.database.dict()
        return "Loaded"


class DeleteOld(Process):
    """ Delete old dat file. """
    database = None
    def process(self):
        """ Delete old dat file. """
        from datoso.database.models.datfile import Dat
        self.database = Dat(seed=self.previous['seed'], name=self.previous['name'])
        self.database.load()
        olddat = self.database.dict()
        result = None
        if 'new_file' in olddat and olddat['new_file'] and os.path.exists(olddat['new_file']):
            if os.path.isdir(olddat['new_file']):
                shutil.rmtree(olddat['new_file'])
            else:
                os.unlink(olddat['new_file'])
            result = "Deleted"

        self.output = self.previous
        return result


class Copy(Process):
    """ Copy files. """
    destination = None
    file = None
    folder = None
    database = None

    def process(self):
        """ Copy files. """
        from datoso.database.models.datfile import Dat
        origin = self.file if self.file else None
        filename = os.path.basename(origin)
        self.destination = self.destination if self.destination else self.previous['path']

        destination = os.path.join(self.folder, self.destination, filename)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        result = None
        if self.previous:
            self.database = Dat(seed=self.previous['seed'], name=self.previous['name'])
            self.database.load()
            if self.database.is_enabled():
                old_file = self.database.dict().get('new_file', '')
                new_file = destination
                if old_file != new_file or config.getboolean('GENERAL', 'Overwrite', fallback=False) or not os.path.exists(destination):
                    if not old_file:
                        result = "Created"
                    elif old_file != new_file:
                        result = "Updated"
                    elif config.getboolean('GENERAL', 'Overwrite', fallback=False):
                        result = "Overwritten"
                    self.previous['new_file'] = destination
                    if os.path.isdir(origin):
                        os.system(f'cp -r "{origin}" "{destination}"')
                    else:
                        os.system(f'cp "{origin}" "{destination}"')
                else:
                    result = "Exists"
            else:
                self.previous['new_file'] = None
                result = "Ignored"
        else:
            os.system(f'cp "{origin}" "{destination}"')
            result = "Copied"

        self.output = self.previous
        return result


class SaveToDatabase(Process):
    """ Save process to database. """
    database = None
    def process(self):
        """ Save process to database. """
        from datoso.database.models.datfile import Dat
        self.database = Dat(**self.previous)
        self.database.save()
        self.database.close()
        self.output = self.previous
        return "Saved"


class Deduplicate(Process):
    """ Save process to database. """
    parent_db = None
    child_db = None

    def get_dat(self, name, seed):
        """ Get dat file. """
        from datoso.database.models.datfile import Dat
        dat = Dat(name=name, seed=seed)
        dat.load()
        return dat

    def process(self):
        """ Save process to database. """
        child_db = Dat(**self.previous)
        child_db.load()
        if not getattr(child_db, 'merge', None) or not getattr(child_db, 'parent', None):
            return "Skipped"
        merged = Dedupe(child_db)
        merged.dedupe()
        merged.save()
        self.output = self.previous
        return "Deduped"


if __name__ == '__main__':
    procesor = Processor()
    procesor.process()
