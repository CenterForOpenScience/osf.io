"""
Update User.comments_viewed_timestamp field & comments model.
Accompanies https://github.com/CenterForOpenScience/osf.io/pull/1762
"""
from modularodm import Q
from framework.auth.core import User
from website.models import Comment
from website.app import init_app
import logging
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    init_app(routes=False, set_backends=True)
    update_comments_viewed_timestamp()
    update_comments()


def update_comments_viewed_timestamp():
    users = User.find(Q('comments_viewed_timestamp', 'ne', None) | Q('comments_viewed_timestamp', 'ne', {}))
    for user in users:
        if user.comments_viewed_timestamp:
            for node in user.comments_viewed_timestamp:
                user.comments_viewed_timestamp[node] = {'node': user.comments_viewed_timestamp[node]}
            user.save()


def update_comments():
    comments = Comment.find()
    for comment in comments:
        comment.root_target = comment.node
        comment.page = Comment.OVERVIEW
        comment.is_hidden = False
        comment.save()


if __name__ == '__main__':
    script_utils.add_file_logger(logger, __file__)
    main()