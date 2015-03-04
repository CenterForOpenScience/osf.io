"""Finds Guids that do not have referents or that point to referents that no longer exist.

E.g. a node was created and given a guid but an error caused the node to
get deleted, leaving behind a guid that points to nothing.
"""
import sys

from framework.guid.model import Guid
from website.app import init_app
from scripts import utils as scripts_utils

import logging
logger = logging.getLogger(__name__)


def main():
    if 'dry' not in sys.argv:
        scripts_utils.add_file_logger(logger, __file__)
    # Set up storage backends
    init_app(routes=False)
    logger.info('{n} invalid GUID objects found'.format(n=len(get_targets())))
    logger.info('Finished.')


def get_targets():
    """Find GUIDs with no referents and GUIDs with referents that no longer exist."""
    # Use a loop because querying MODM with Guid.find(Q('referent', 'eq', None))
    # only catches the first case.
    ret = []
    for each in Guid.find():
        logger.info('GUID {} has no referent.'.format(each._id))
        if each.referent is None:
            ret.append(each)
    return ret

if __name__ == '__main__':
    main()
