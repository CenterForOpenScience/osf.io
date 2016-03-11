"""
Update Comment.target and Comment.root_target to use the Guid instead of
Comment, Node and StoredFileNode objects.
"""
import logging
import sys

from framework.guid.model import Guid
from framework.transactions.context import TokuTransaction

from website.models import Comment
from website.files.models import StoredFileNode
from website.app import init_app

from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    update_comment_targets_to_guids()


def update_comment_targets_to_guids():
    comments = Comment.find()
    for comment in comments:
        # Skip comments on deleted files
        if not comment.target:
            continue
        if isinstance(comment.root_target, StoredFileNode):
            comment.root_target = comment.root_target.get_guid()
        elif comment.root_target:
            comment.root_target = Guid.load(comment.root_target._id)

        if isinstance(comment.target, StoredFileNode):
            comment.target = comment.target.get_guid()
        else:
            comment.target = Guid.load(comment.target._id)

        comment.save()
        logger.info('Migrated root_target and target for comment {0}'.format(comment._id))

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')
