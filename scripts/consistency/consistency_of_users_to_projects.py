"""Check for consistency of users to projects

"""
import logging
from website.app import init_app
from website import models
from modularodm import Q
from scripts import utils as script_utils

app = init_app()
logger = logging.getLogger(__name__)


def check_consistency_of_users_to_projects():

    nodes = models.Node.find(
        Q('is_deleted', 'eq', False)
    )
    count = 0
    for node in nodes:
        if node._id not in node.creator.created:
            logger.info('Creator {} is inconsistent in reference with node {}'.format(node.creator._id, node._id))
            count += 1
        for contributor in node.contributors:
            if node._id not in contributor.contributed:
                logger.info('Contributor {} is inconsistent in reference with node {}'.format(contributor._id, node._id))
                count += 1

    if count == 0:
        logger.info("Consistency of users to projects' check is done. There is no inconsistency found.")
    else:
        logger.info("Consistency of users to projects' check is done. There are {} inconsistency found.".format(count))


if __name__ == '__main__':
    script_utils.add_file_logger(logger, __file__)
    check_consistency_of_users_to_projects()
