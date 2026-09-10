"""
Clears deleted field value for all restored OsfStorageFileNode objects
as restore() method did not remove it and such files after restore from TrashedFileNode are not shown on UI
"""
import logging

from django.db import transaction
from django.core.management.base import BaseCommand

from addons.osfstorage.models import OsfStorageFileNode


logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes',
        )

    def handle(self, *args, **options):
        files_to_fix = OsfStorageFileNode.objects.filter(deleted__isnull=False)
        file_ids = list(files_to_fix.values_list('_id', flat=True))
        dry_run = options.get('dry_run', False)

        if dry_run:
            logger.info(f'Running in dry-run mode, the following files would be fixed: {file_ids}')
            self.stdout.write(f'Running in dry-run mode, the following files would be fixed: {file_ids}')
            return

        with transaction.atomic():
            for file in files_to_fix:
                file.deleted = None

            OsfStorageFileNode.objects.bulk_update(files_to_fix, ['deleted'], batch_size=1000)

        logger.info(f'The following files have been fixed: {file_ids}')
        self.stdout.write(f'The following files have been fixed: {file_ids}')
