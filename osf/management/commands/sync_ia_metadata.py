from django.core.management.base import BaseCommand
from osf.models import Registration
from framework.celery_tasks import update_ia_metadata
from django.db.models import F
import logging
logger = logging.getLogger(__name__)

class IAMetadataError(Exception):
    pass

get_ia_field = lambda field : Registration.IA_MAPPED_NAMES.get(field, field)

mirrored_attrs = list(Registration.SYNCED_WITH_IA)


mirrored_fields = mirrored_attrs + ['subjects', 'tags', 'affiliated_institutions']


def sync_ia_metadata(guids):
    registrations = Registration.objects.filter(guids___id__in=guids).order_by('guids___id')
    data = registrations.values(
        *mirrored_attrs,
    ).annotate(
        subjects=F('subjects__text'),
        affiliated_institutions=F('affiliated_institutions__name'),
        tags=F('tags__name'),
    )
    for registration, values in zip(registrations, data):
        update_ia_metadata(registration, values)


class Command(BaseCommand):
    """
    Checks all IA items in collection to see if they are synced with the OSF
    """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--collection',
            type=str,
            action='store',
            dest='ia_collection',
            help='The Internet Archive collection that we are checking for parity',
        )
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )
        parser.add_argument(
            'guids',
            type=str,
            nargs='+',
            help='List of guids to archive.',
        )

    def handle(self, *args, **options):
        guids = options.get('guids', None)
        sync_ia_metadata(guids)