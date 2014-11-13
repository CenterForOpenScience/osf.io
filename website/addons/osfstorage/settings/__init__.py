import logging
from .defaults import *  # noqa

try:
    from .local import *  # noqa
except ImportError as error:
    logging.warn('No local.py settings file found')
