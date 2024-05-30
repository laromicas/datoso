"""Configuration module."""
import configparser
import os
from pathlib import Path

from datoso import ROOT_FOLDER, __app_name__

HOME = Path.home()
XDG_CONFIG_HOME = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')).expanduser()

def get_seed_name(seed):
    """Get seed name."""
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

config_paths = [
    ROOT_FOLDER / 'datoso.ini',
    XDG_CONFIG_HOME / 'datoso/datoso.config',
    HOME / '.datosorc',
    Path.cwd() / '.datosorc',
]

config = Config(allow_no_value=True)
config.optionxform = lambda option: option
for config_path in config_paths:
    config.read(config_path)
