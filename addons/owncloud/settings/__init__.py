import logging
from addons.owncloud.settings.defaults import *  # noqa

logger = logging.getLogger(__name__)
try:
    from addons.owncloud.settings.local import *  # noqa
except ImportError:
    logger.warning('No local.py settings file found')
