import logging
from addons.fedora.settings.defaults import *  # noqa

logger = logging.getLogger(__name__)
try:
    from addons.fedora.settings.local import *  # noqa
except ImportError as error:
    logger.warn('No local.py settings file found')
