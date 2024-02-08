import logging
from .defaults import *  # noqa

logger = logging.getLogger(__name__)
try:
    from .local import *  # noqa
except ImportError:
    logger.warning('No local.py settings file found')
