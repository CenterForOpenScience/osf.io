# -*- coding: utf-8 -*-
import sys
import logging
import django
from scripts import utils as script_utils
from django.db import transaction
from django.db.models import Exists, OuterRef

from website.app import init_app

django.setup()
logger = logging.getLogger(__name__)


def fix_bookmark_permissions(dry_run=True):
    from osf.models import OSFUser
    from django.contrib.auth.models import Group

    users_without_perms = OSFUser.objects.filter(is_active=True).annotate(
        has_perm=Exists(Group.objects.filter(name__startswith='collections_', user=OuterRef('pk')))
    ).exclude(has_perm=True)
    logger.info('Found {} target users'.format(users_without_perms.count()))

    for user in users_without_perms:
        for col in user.collection_set.filter(deleted__isnull=True):
            logger.info('Adding user {} to admin group for {}'.format(user._id, col))
            col.get_group('admin').user_set.add(user)

def main(dry_run=True):
    fix_bookmark_permissions(dry_run)
    if dry_run:
        # When running in dry_run mode force the transaction to rollback
        raise Exception('Dry Run complete -- not actually saved')

def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)

    # Finally run the migration
    with transaction.atomic():
        main(dry_run=dry_run)

if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    run_main(dry_run=dry_run)
