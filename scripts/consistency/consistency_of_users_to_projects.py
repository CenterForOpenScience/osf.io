"""Check for consistency of users to projects

"""
import logging
import sys

from modularodm import Q

from website.app import init_app
from website import models
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def check_consistency_of_users_to_projects():

    nodes = models.Node.find(
        Q('is_deleted', 'eq', False)
    )
    no_creator, creator_ref, contrib_ref = [], [], []
    for node in nodes:
        if not node.creator:
            logger.info('Node {} has no creator'.format(node._id))
            no_creator.append(node)
        elif node and node._id not in node.creator.created:
            logger.info('Creator {} is inconsistent in reference with node {}'.format(node.creator._id, node._id))
            creator_ref.append(node)
        for contributor in node.contributors:
            if node and node._id not in contributor.contributed:
                logger.info('Contributor {} is inconsistent in reference with node {}'.format(contributor._id, node._id))
                contrib_ref.append(node)

    count = len(no_creator) + len(creator_ref) + len(contrib_ref)
    if count == 0:
        logger.info("Consistency of users to projects' check is done. There is no inconsistency found.")
    else:
        logger.info("Consistency of users to projects' check is done. There are {} inconsistency found.".format(count))
    return no_creator, creator_ref, contrib_ref


if __name__ == '__main__':
    app = init_app(routes=False)
    if 'dry' not in sys.argv:
        script_utils.add_file_logger(logger, __file__)
    check_consistency_of_users_to_projects()
