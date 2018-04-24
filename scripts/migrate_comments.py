import logging
import sys

from website.app import setup_django
setup_django()
from django.db import transaction

from osf.models import Comment
from website.app import init_app
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)


def main():
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        scripts_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        comments = Comment.objects.filter(is_deleted=False)
        count = 0
        for comment in comments:
            if comment.root_target:
                if hasattr(comment.root_target.referent, 'is_deleted') and comment.root_target.referent.is_deleted:
                    comment.root_target = None
                    comment.save()
                    count += 1
                if comment.root_target and hasattr(comment.root_target.referent, 'deleted') and comment.root_target.referent.deleted:
                    comment.root_target = None
                    comment.save()
                    count += 1
        logger.info('Total download number of commnet migrated is {}.'.format(count))


if __name__ == '__main__':
    init_app(routes=False)
    main()
