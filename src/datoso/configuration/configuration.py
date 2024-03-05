""" Configuration module. """
import configparser
import os

from datoso import __app_name__, ROOT_FOLDER

def get_seed_name(seed):
    """ Get seed name. """
    return seed.replace(f'{__app_name__}_seed_', '')


class Config(configparser.ConfigParser):
    def get(self, section, option, **kwargs):
        envvar = f'{section}.{option.upper()}'
        if envvar in os.environ:
            return os.environ[envvar]
        try:
            return super().get(section, option, **kwargs)
        except configparser.NoOptionError:
            return None

    def getboolean(self, section, option, **kwargs):
        envvar = f'{section}.{option.upper()}'
        if envvar in os.environ:
            return os.environ[envvar].lower() in ['true', 'yes', '1']
        try:
            return super().getboolean(section, option, **kwargs)
        except configparser.NoOptionError:
            return None


config = Config(allow_no_value=True)
config.optionxform = lambda option: option
config.read(os.path.join(ROOT_FOLDER, 'datoso.ini'))
config.read(os.path.expanduser('~/.datosorc'))
config.read(os.path.join(os.getcwd(), '.datosorc'))
