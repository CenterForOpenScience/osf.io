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

    def handle(self, *args, **options):
        with transaction.atomic():
            files_to_fix = OsfStorageFileNode.objects.filter(deleted__isnull=False)
            for file in files_to_fix:
                file.deleted = None

            OsfStorageFileNode.objects.bulk_update(files_to_fix, ['deleted'], batch_size=1000)
