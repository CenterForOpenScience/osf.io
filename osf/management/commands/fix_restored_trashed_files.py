"""
Clears deleted, deleted_on, deleted_by values for all restored OsfStorageFileNode objects
as restore() method did not remove them and such files after restore from TrashedFileNode are not shown on UI
"""
import logging

from django.db import transaction
from django.db.models import Q
from django.core.management.base import BaseCommand

from addons.osfstorage.models import OsfStorageFileNode


logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        with transaction.atomic():
            files_to_fix = OsfStorageFileNode.objects.filter(
                Q(deleted__isnull=False) | Q(deleted_by__isnull=False) | Q(deleted_on__isnull=False),
            )
            for file in files_to_fix:
                file.deleted = None
                file.deleted_by = None
                file.deleted_on = None

            OsfStorageFileNode.objects.bulk_update(files_to_fix, ['deleted', 'deleted_by', 'deleted_on'], batch_size=1000)
