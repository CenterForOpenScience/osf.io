import logging
from .defaults import *  # noqa

logger = logging.getLogger(__name__)
try:
    from .local import *  # noqa
except ImportError as error:
    logger.warn('No local.py settings file found')

# NextCloud User to ePPN
DEBUG_NCUSER_TO_EPPN_MAP = dict(
    [(DEBUG_EPPN_TO_NCUSER_MAP[k], k) for k in DEBUG_EPPN_TO_NCUSER_MAP]
)
