import logging
from addons.nextcloud.settings.defaults import *  # noqa

logger = logging.getLogger(__name__)
try:
    from addons.nextcloud.settings.local import *  # noqa
except ImportError as error:
    logger.warn('No local.py settings file found')
