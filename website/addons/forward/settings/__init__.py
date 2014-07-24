import logging
from .defaults import *


logger = logging.getLogger('website.addons.forward')

try:
    from .local import *
except ImportError as error:
    logger.warn('No local.py settings file found')
