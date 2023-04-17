""" Configuration module """
__all__ = ['config', 'logger', 'ROOT_FOLDER']

import os
from datoso import ROOT_FOLDER

from datoso.configuration.configuration import config
from datoso.configuration.logger import logger

SEEDS_FOLDER = os.path.join(ROOT_FOLDER, 'seeds')
