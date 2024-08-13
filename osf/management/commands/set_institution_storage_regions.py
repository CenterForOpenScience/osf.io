import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import Institution, InstitutionStorageRegion
from addons.osfstorage.models import Region

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Set storage regions for institutions.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '-d',
            '--dry',
            action='store_true',
            dest='dry_run',
            help='If true, check institution and region only'
        )
        parser.add_argument(
            '-i',
            '--institution',
            type=str,
            required=True,
            help='Select the institution to add the storage region to'
        )
        parser.add_argument(
            '-r',
            '--region',
            type=str,
            required=True,
            help='Select the storage region to be added to the institution'
        )
        parser.add_argument(
            '-p',
            '--preferred',
            action='store_true',
            dest='is_preferred',
            help='Set the storage region as the preferred choice for the institution'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        if dry_run:
            logger.warning('Dry Run: This is a dry-run pass!')
        institution_id = options['institution']
        region_id = options['region']
        is_preferred = options.get('is_preferred', False)
        with transaction.atomic():
            set_institution_storage_regions(institution_id, region_id, is_preferred=is_preferred)
            if dry_run:
                raise RuntimeError('Dry run -- transaction rolled back')


def set_institution_storage_regions(institution_id, region_id, is_preferred=False):

    # Verify institution and region
    try:
        institution = Institution.objects.get(_id=institution_id)
        region = Region.objects.get(_id=region_id)
    except (Institution.DoesNotExist, Region.DoesNotExist) as e:
        logger.error(f'Institution and/or Region not found: error={e}')
        return
    # Get or set region for institution
    if region in institution.storage_regions.all():
        logger.warning(f'Region [{region._id}] already set for Institution [{institution._id}]')
        institution_storage_region = InstitutionStorageRegion.objects.get(
            institution=institution,
            storage_region=region
        )
        if institution_storage_region.is_preferred:
            logger.warning(f'Region [{region._id}] already set as preferred for Institution [{institution._id}]')
            return
    else:
        institution_storage_region = InstitutionStorageRegion.objects.create(
            institution=institution,
            storage_region=region
        )
        logger.info(f'Region [{region._id}] has been added to Institution [{institution._id}]')

    # Make sure there is only one preferred region
    try:
        existing_preferred_institution_storage_region = InstitutionStorageRegion.objects.get(
            institution=institution,
            is_preferred=True,
        )
    # Case 1: always set the region as preferred if there is no preferred region for the institution;
    #         this executes even if the option `-p` / `--preferred` is not provided
    except InstitutionStorageRegion.DoesNotExist:
        institution_storage_region.is_preferred = True
        institution_storage_region.save()
        logger.info(f'Region [{region._id}] has been set as preferred choice for Institution [{institution._id}]')
        return
    # Case 2: do nothing and return if preferred region exists and if `is_preferred` is not set
    if not is_preferred:
        return
    # Case 3: if `is_preferred` is set, clear the existing preferred region before setting the new one
    existing_preferred_institution_storage_region.is_preferred = False
    existing_preferred_institution_storage_region.save()
    logger.info(f'The old preferred region has been removed from Institution [{institution._id}]')
    institution_storage_region.is_preferred = True
    institution_storage_region.save()
    logger.info(f'Region [{region._id}] has been set as the preferred choice for Institution [{institution._id}]')
