import logging

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db.models import F, Value
from django.db.models.functions import Concat, Replace

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Adds Colon (':') delineators to s3 buckets to separate them from them from their subfolder, so `<bucket_name>`
    becomes `<bucket_name>:/` , the root path. Folder names will also be updated to maintain consistency.

    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--reverse',
            action='store_true',
            dest='reverse',
            help='Unsets date_retraction'
        )

    def handle(self, *args, **options):
        reverse = options.get('reverse', False)
        if reverse:
            reverse_update_folder_names()
        else:
            update_folder_names()


def update_folder_names():
    NodeSettings = apps.get_model('addons_s3', 'NodeSettings')

    # Update folder_id for all records
    NodeSettings.objects.exclude(
        folder_name__contains=':/'
    ).update(
        folder_id=Concat(F('folder_id'), Value(':/'))
    )

    # Update folder_name for records containing '('
    NodeSettings.objects.filter(
        folder_name__contains=' ('
    ).exclude(
        folder_name__contains=':/'
    ).update(
        folder_name=Replace(F('folder_name'), Value(' ('), Value(':/ ('))
    )
    NodeSettings.objects.exclude(
        folder_name__contains=':/'
    ).exclude(
        folder_name__contains=' ('
    ).update(
        folder_name=Concat(F('folder_name'), Value(':/'))
    )
    logger.info('Update Folder Names/IDs complete')


def reverse_update_folder_names():
    NodeSettings = apps.get_model('addons_s3', 'NodeSettings')

    # Reverse update folder_id for all records
    NodeSettings.objects.update(folder_id=Replace(F('folder_id'), Value(':/'), Value('')))

    # Reverse update folder_name for records containing ':/ ('
    NodeSettings.objects.filter(folder_name__contains=':/ (').update(
        folder_name=Replace(F('folder_name'), Value(':/ ('), Value(' ('))
    )
    NodeSettings.objects.filter(folder_name__contains=':/').update(
        folder_name=Replace(F('folder_name'), Value(':/'), Value(''))
    )
    logger.info('Reverse Update Folder Names/IDs complete')
