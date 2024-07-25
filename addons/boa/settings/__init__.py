import logging

from addons.boa.settings.defaults import *  # noqa

logger = logging.getLogger(__name__)

try:
    from addons.boa.settings.local import *  # noqa
except ImportError:
    logger.warning('No local.py settings file found')
