"""Finds Guids that do not have referents or that point to referents that no longer exist.

E.g. a node was created and given a guid but an error caused the node to
get deleted, leaving behind a guid that points to nothing.
"""
import sys

from modularodm import Q
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
    # NodeFiles were once a GuidStored object and are no longer used any more.
    # However, they still exist in the production database. We just skip over them
    # for now, but they can probably need to be removed in the future.
    # There were also 10 osfguidfile objects that lived in a corrupt repo that
    # were not migrated to OSF storage, so we skip those as well. /sloria /jmcarp
    for each in Guid.find(Q('referent.1', 'nin', ['nodefile', 'osfguidfile'])):
        if each.referent is None:
            logger.info('GUID {} has no referent.'.format(each._id))
            ret.append(each)
    return ret

if __name__ == '__main__':
    main()
