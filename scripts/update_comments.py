"""
Update User.comments_viewed_timestamp field & comments model.
Accompanies https://github.com/CenterForOpenScience/osf.io/pull/1762
"""
import logging
import sys

from modularodm import Q

from framework.auth.core import User
from framework.transactions.context import TokuTransaction

from website.models import Comment
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    update_comments_viewed_timestamp()
    update_comments()


def update_comments_viewed_timestamp():
    users = User.find(Q('comments_viewed_timestamp', 'ne', None) | Q('comments_viewed_timestamp', 'ne', {}))
    for user in users:
        if user.comments_viewed_timestamp:
            for node in user.comments_viewed_timestamp:
                user.comments_viewed_timestamp[node] = {'node': user.comments_viewed_timestamp[node]}
            user.save()
            logger.info('Migrated timestamp for user {0}'.format(user._id))


def update_comments():
    comments = Comment.find()
    for comment in comments:
        comment.root_target = comment.node
        comment.page = Comment.OVERVIEW
        comment.save()


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')