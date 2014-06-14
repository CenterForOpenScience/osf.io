import logging
from .defaults import *

try:
    from .local import *
except ImportError as error:
    logging.warn('No local.py settings file found')
