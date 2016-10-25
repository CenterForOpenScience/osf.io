import logging
from website.addons.owncloud.settings.defaults import *  # noqa

logger = logging.getLogger(__name__)
try:
    from website.addons.owncloud.settings.local import *  # noqa
except ImportError as error:
    logger.warn('No local.py settings file found')
