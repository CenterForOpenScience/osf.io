import logging
from .defaults import *


logger = logging.getLogger('website.addons.github')

try:
    from .local import *
except ImportError as error:
    logger.warn('No local.py settings file found')
