import logging
from website.addons.fedora.settings.defaults import *  # noqa

logger = logging.getLogger(__name__)
try:
    from website.addons.fedora.settings.local import *  # noqa
except ImportError as error:
    logger.warn('No local.py settings file found')
