""" Configuration module. """
import configparser
import os

from datoso import __app_name__, ROOT_FOLDER

config = configparser.ConfigParser(allow_no_value=True)
config.optionxform = lambda option: option
config.read(os.path.join(ROOT_FOLDER, 'datoso.ini'))
config.read(os.path.expanduser('~/.datosorc'))
config.read(os.path.join(os.getcwd(), '.datosorc'))


def get_seed_name(seed):
    """ Get seed name. """
    return seed.replace(f'{__app_name__}_seed_', '')
