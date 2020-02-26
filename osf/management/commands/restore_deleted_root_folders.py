# -*- coding: utf-8 -*-
import logging
import datetime

from bulk_update.helper import bulk_update
from django.core.management.base import BaseCommand

from osf.models import BaseFileNode

logger = logging.getLogger(__name__)

def restore_deleted_root_folders(dry_run=False):
    deleted_roots = BaseFileNode.objects.filter(
        type='osf.trashedfolder',
        is_root=True,
        name='',
        provider='osfstorage'
    )

    logger.info('Restoring {} deleted osfstorage root folders'.format(len(deleted_roots)))

    for i, folder in enumerate(deleted_roots, 1):
        folder.deleted_on = None
        folder.type = 'osf.osfstoragefolder'

    if not dry_run:
        bulk_update(deleted_roots, update_fields=['deleted_on', 'type'])


class Command(BaseCommand):
    """Restore deleted osfstorage root folders
    """
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Run queries but do not write files',
        )

    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))

        dry_run = options['dry_run']

        if dry_run:
            logger.info('DRY RUN. Data will not be saved.')

        restore_deleted_root_folders(dry_run)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
