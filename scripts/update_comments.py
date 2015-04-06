"""
Update User.comments_viewed_timestamp field & comments model.
Accompanies https://github.com/CenterForOpenScience/osf.io/pull/1762
"""
import sys
from framework.auth.core import User
from website.models import Comment
from website.app import init_app
import logging
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main(dry=True):
    init_app(routes=False)
    update_comments_viewed_timestamp(dry=dry)
    update_comments(dry=dry)


def update_comments_viewed_timestamp(dry=True):
    users = User.find()
    for user in users:
        if not dry:
            if user.comments_viewed_timestamp:
                for node in user.comments_viewed_timestamp:
                    user.comments_viewed_timestamp[node] = {'node': user.comments_viewed_timestamp[node]}
                user.save()
        logger.info('User {}\'s comments_viewed_timestamp updated.'.format(user._id))


def update_comments(dry=True):
    comments = Comment.find()
    for comment in comments:
        if not dry:
            comment.root_target = comment.node
            comment.page = 'node'
            comment.is_hidden = False
            comment.save()
        logger.info('Comment {}\'s model updated.'.format(comment._id))


if __name__ == '__main__':
    script_utils.add_file_logger(logger, __file__)
    main(dry='dry' in sys.argv)