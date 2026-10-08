import logging

from django.core.management.base import BaseCommand

from addons.osfstorage import settings as osfstorage_settings
from addons.osfstorage.models import Region
from osf.models import FileVersion, Preprint
from osf.models.admin_log_entry import AdminLogEntry, PREPRINT_RECOVERED, PREPRINT_RESTORED

logger = logging.getLogger(__name__)


def _bucket_of(region):
    return (region.waterbutler_settings or {}).get('storage', {}).get('bucket')


def find_recovered_preprints(guids=None):
    if guids:
        object_ids = list(guids)
    else:
        object_ids = list(
            AdminLogEntry.objects.filter(
                action_flag__in=[PREPRINT_RECOVERED, PREPRINT_RESTORED],
            ).order_by().values_list('object_id', flat=True).distinct()  # order_by() clears the default ordering that defeats distinct()
        )
    for object_id in object_ids:
        try:
            preprint = Preprint.load(object_id)
        except ValueError:
            logger.warning(f'{object_id}: not a valid preprint guid, skipping')
            continue
        if preprint is None:
            logger.warning(f'{object_id}: preprint not found, skipping')
            continue
        yield preprint


def resolve_version_region(version, regions, client=None):
    location = version.location or {}
    bucket = location.get('bucket') or location.get(osfstorage_settings.WATERBUTLER_RESOURCE)
    if bucket:
        matches = [r for r in regions if _bucket_of(r) == bucket]
        if len(matches) == 1:
            return matches[0], 'location bucket'

    blob_name = location.get('object')
    if not client or not blob_name:
        return None, (
            f'location bucket "{bucket}" does not identify exactly one region; '
            'rerun with --probe to look the blob up in each region bucket'
        )
    holders = [r for r in regions if _bucket_of(r) and client.bucket(_bucket_of(r)).blob(blob_name).exists()]
    if not holders:
        return None, 'blob not found in any region bucket (purged?)'
    if version.region in holders:
        return version.region, 'probe (current region holds the blob)'
    if len(holders) > 1:
        return None, 'blob found in several region buckets; ambiguous'
    return holders[0], 'probe'


def repair_preprint_regions(preprints, dry_run=False, client=None):
    regions = list(Region.objects.all())
    stats = {'checked': 0, 'versions_fixed': 0, 'preprints_fixed': 0, 'unresolved': 0}

    for preprint in preprints:
        primary_file = preprint.primary_file
        if primary_file is None:
            logger.info(f'{preprint._id}: no primary file, skipping')
            continue
        stats['checked'] += 1

        latest_region_id = None  # region the newest version has, or will have once repaired (also in a dry run)
        for version in primary_file.versions.select_related('region').order_by('created'):
            latest_region_id = version.region_id
            if version.purged:
                logger.warning(f'{preprint._id}: version {version.identifier} (FV {version.id}) is purged, skipping')
                stats['unresolved'] += 1
                continue
            true_region, reason = resolve_version_region(version, regions, client=client)
            if true_region is None:
                logger.warning(f'{preprint._id}: version {version.identifier} (FV {version.id}) unresolved: {reason}')
                stats['unresolved'] += 1
                continue
            latest_region_id = true_region.id
            if version.region_id == true_region.id:
                continue
            logger.info(
                f'{preprint._id}: FV {version.id} region {version.region and version.region._id} -> '
                f'{true_region._id} ({reason})'
            )
            stats['versions_fixed'] += 1
            if not dry_run:
                # Queryset update on purpose: `FileVersion.save()` runs full_clean(), and the `location` written by
                # Waterbutler in prod (`bucket`, no `folder`) fails `validate_location`. Only the region changes here.
                FileVersion.objects.filter(pk=version.pk).update(region=true_region)

        if latest_region_id and latest_region_id != preprint.region_id:
            logger.info(f'{preprint._id}: preprint region {preprint.region_id} -> {latest_region_id}')
            stats['preprints_fixed'] += 1
            if not dry_run:
                preprint.set_storage_region(latest_region_id)

    return stats


class Command(BaseCommand):
    help = (
        'Repair FileVersion/Preprint storage regions of admin-recovered preprints whose file copy was relabeled '
        'to another region without moving the blob (Waterbutler NoSuchKey, "Missing PDF file").'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry_run', action='store_true', default=False, help='Log changes without saving')
        parser.add_argument('--guids', nargs='*', default=None, help='Only these preprint guids (e.g. stzmk_v1)')
        parser.add_argument(
            '--probe',
            action='store_true',
            default=False,
            help='When a version location has no bucket, look the blob up in every region bucket via GCS',
        )

    def handle(self, *args, **options):
        client = None
        if options['probe']:
            from google.cloud.storage.client import Client
            from google.oauth2.service_account import Credentials
            from website.settings import GCS_CREDS
            client = Client(credentials=Credentials.from_service_account_file(GCS_CREDS))

        if options['dry_run']:
            logger.info('DRY RUN. Data will not be saved.')
        stats = repair_preprint_regions(
            find_recovered_preprints(options['guids']), dry_run=options['dry_run'], client=client,
        )
        logger.info(f'Done: {stats}')
