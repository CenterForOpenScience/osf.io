import logging
from django.core.management.base import BaseCommand

from osf.models import Preprint

logger = logging.getLogger(__name__)


def reindex_versioned_preprints(dry_run=False, batch_size=100, provider_id=None, guids=None):
    if guids:
        preprints = Preprint.objects.filter(guids___id__in=guids)
    else:
        preprints = Preprint.objects.filter(versioned_guids__isnull=False).distinct()

        if provider_id:
            preprints = preprints.filter(provider___id=provider_id)

    preprints = preprints.filter(is_published=True)

    total_count = preprints.count()
    logger.info(f'{"[DRY RUN] " if dry_run else ""}Found {total_count} versioned preprints to re-index')

    if total_count == 0:
        logger.info('No preprints to re-index')
        return

    processed = 0
    for preprint in preprints.iterator(chunk_size=batch_size):
        processed += 1

        if dry_run:
            logger.info(
                f'[DRY RUN] Would re-index preprint {preprint._id} '
                f'(version {preprint.versioned_guids.first().version if preprint.versioned_guids.exists() else "N/A"}, '
                f'date_created_first_version={preprint.date_created_first_version}) '
                f'[{processed}/{total_count}]'
            )
        else:
            try:
                preprint.update_search()
            except Exception as e:
                logger.error(f'Failed to re-index preprint {preprint._id}: {e}')

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}Completed. '
        f'{"Would have re-indexed" if dry_run else "Re-indexed"} {processed} preprints'
    )


class Command(BaseCommand):
    help = (
        'Re-index all versioned preprints to Elasticsearch to ensure computed properties '
        'like date_created_first_version are up to date.'
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Preview what would be re-indexed without actually making changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of preprints to process in each batch (default: 100)',
        )
        parser.add_argument(
            '--provider',
            type=str,
            help='Optional provider ID to filter preprints',
        )
        parser.add_argument(
            '--guids',
            type=str,
            nargs='+',
            help='Optional list of specific preprint GUIDs to re-index',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        batch_size = options.get('batch_size', 100)
        provider_id = options.get('provider')
        guids = options.get('guids')

        if dry_run:
            logger.info('=' * 60)
            logger.info('DRY RUN MODE - No changes will be made')
            logger.info('=' * 60)

        reindex_versioned_preprints(
            dry_run=dry_run,
            batch_size=batch_size,
            provider_id=provider_id,
            guids=guids
        )
