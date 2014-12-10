# encoding: utf-8
import logging

from .defaults import *


logger = logging.getLogger()


try:
    from .local import *
except ImportError:
    logger.warning('No local.py found.')
    logger.warning('Using defaults.')
