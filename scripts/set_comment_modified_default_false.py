"""
For unmodified comments, change comment.modified from None to False since the default value
has been set to False on the comment model.
"""

import sys
import logging
from modularodm import Q

from scripts import utils as script_utils
from website.app import init_app
from website.project.model import Comment

logger = logging.getLogger(__name__)


def main():
    init_app(routes=False)
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    do_migration(get_targets(), dry=dry)


def get_targets():
    return Comment.find(Q('modified', 'eq', None))


def do_migration(records, dry=True):
    count = 0
    for comment in records:
        logger.info('Updating comment {}'.format(comment._id))
        count +=1
        if not dry:
            comment.modified = False
            comment.save()
    logger.info('{} comments updated'.format(count))


if __name__ == '__main__':
    main()
