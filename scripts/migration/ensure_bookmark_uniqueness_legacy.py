import argparse
import logging

from modularodm import Q

from framework.auth.core import User
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.project.model import Node


logger = logging.getLogger(__name__)

def get_targets():
    logger.info('Acquiring targets...')
    targets = [u for u in User.find() if Node.find(Q('is_bookmark_collection', 'eq', True) & Q('is_deleted', 'eq', False) & Q('creator', 'eq', u._id)).count() > 1]
    logger.info('Found {} target users.'.format(len(targets)))
    return targets

def migrate():
    targets = get_targets()
    total = len(targets)
    for i, user in enumerate(targets):
        logger.info('({}/{}) Preparing to migrate User {}'.format(i + 1, total, user._id))
        bookmarks = Node.find(Q('is_bookmark_collection', 'eq', True) & Q('creator', 'eq', user._id)).sort('-date_modified')

        bookmark_to_keep = None
        for n in bookmarks:
            if n.nodes:
                bookmark_to_keep = n
        bookmark_to_keep = bookmark_to_keep or bookmarks[0]
        logger.info('Marking Node {} as primary Bookmark Collection for User {}, preparing to delete others'.format(bookmark_to_keep._id, user._id))
        for n in bookmarks:
            if n._id != bookmark_to_keep._id:
                n.is_deleted = True
                n.save()
        logger.info('Successfully migrated User {}'.format(user._id))
    logger.info('Successfully migrated {} users'.format(total))

def main():
    parser = argparse.ArgumentParser(
        description='Ensures every user has only one bookmark collection.'
    )
    parser.add_argument(
        '--dry',
        action='store_true',
        dest='dry_run',
        help='Run migration and roll back changes to db',
    )
    pargs = parser.parse_args()
    if not pargs.dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate()
        if pargs.dry_run:
            raise Exception('Dry Run -- Transaction aborted.')

if __name__ == '__main__':
    main()
