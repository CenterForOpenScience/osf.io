"""Fixes a number of bookmark collections whose creator is not a contributor."""
import sys
import logging
from website.app import setup_django
from scripts import utils as script_utils
from django.db import transaction
from django.db.models import F

setup_django()
from osf.models import Collection, Contributor

logger = logging.getLogger(__name__)

def do_migration():
    # Find bookmark collections whose creator is not a contributor
    bookmarks = Collection.objects.filter(
        is_bookmark_collection=True,
        is_deleted=False,
    ).exclude(_contributors=F('creator_id'))
    for bookmark in bookmarks:
        logger.info('Adding User {} as a contributor to Collection {}'.format(bookmark.creator._id, bookmark._id))
        Contributor.objects.create(
            user=bookmark.creator,
            node=bookmark,
            visible=True,
            read=True,
            write=True,
            admin=True,
        )
    logger.info('Finished migrating {} bookmark Collections.'.format(bookmarks.count()))

def main(dry=True):
    # Start a transaction that will be rolled back if any exceptions are un
    with transaction.atomic():
        do_migration()
        if dry:
            # When running in dry mode force the transaction to rollback
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
