"""
For unmodified comments, change comment.modified from None to False since the default value
has been set to False on the comment model.
"""

import sys
import logging
from modularodm import Q

from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.project.model import Comment

logger = logging.getLogger(__name__)


def main(dry=True):
    init_app(routes=False)
    with TokuTransaction():
        do_migration(get_targets())
        if dry:
            raise Exception('Abort Transaction - Dry Run')


def get_targets():
    return Comment.find(Q('modified', 'eq', None))


def do_migration(records):
    logger.info('Updating {} comments'.format(len(records)))
    for comment in records:
        logger.info('Updating comment {}'.format(comment._id))
        comment.modified = False
        comment.save()


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
