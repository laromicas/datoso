""" Configuration module. """
import configparser
import os

from datoso import ROOT_FOLDER

config = configparser.ConfigParser(allow_no_value=True)
config.optionxform = lambda option: option
config.read(os.path.join(ROOT_FOLDER, 'datoso.ini'))
config.read(os.path.join(os.getcwd(), '.datosorc'))
config.read(os.path.join(os.path.expanduser('~'), '.datosorc'))
