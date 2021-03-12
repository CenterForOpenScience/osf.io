import logging
from .defaults import *  # noqa

logger = logging.getLogger(__name__)
try:
    from .local import *  # noqa
except ImportError:
    logger.warn('No local.py settings file found')

# compatibility for institutions_utils.py
DEFAULT_BASE_FOLDER = DEFAULT_BASE_BUCKET.strip('/')
