import logging

from osf.models import RegistrationProvider
from django.core.management.base import BaseCommand
from osf_pigeon.pigeon import create_subcollection
from website import settings


logger = logging.getLogger(__file__)


def populate_internet_archives_collections(version_id='v1', dry_run=False):
    for provider in RegistrationProvider.objects.all():
        provider_id = f'collection-osf-registration-providers-{provider._id}-{version_id}'
        if not dry_run:
            create_subcollection(
                provider_id,
                settings.IA_ACCESS_KEY,
                settings.IA_SECRET_KEY,
                metadata={
                    'title': provider.name
                },
                parent_collection=settings.IA_ROOT_COLLECTION,
            )
        logger.info(f'{"DRY_RUN" if dry_run else ""} collection for {provider._id} collection created with id {provider_id} ')


class Command(BaseCommand):
    help = """
    This command populates internet archive with collections for our registrations are to go in. `version_id` here
     can indicate the sequential version_id such as `v1`, or the testing enviorment `staging_v1`.
     """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='makes everything but logging a no-op',
        )
        parser.add_argument(
            '--version_id',
            dest='version_id',
            help='indicates the sequential version_id such as `v1`, or the testing environment `staging_v1`.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        version_id = options.get('version_id', settings.IA_ID_VERSION)

        populate_internet_archives_collections(version_id, dry_run=dry_run)
