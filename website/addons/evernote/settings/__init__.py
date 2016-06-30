import logging
from .defaults import *  # noqa

logger = logging.getLogger(__name__)

try:
    from .local import *  # noqa
except ImportError as error:
    logger.warn('No local.py settings file found')

BASE_URL = 'https://www.evernote.com' if not EVERNOTE_SANDBOX  \
       else 'https://sandbox.evernote.com'