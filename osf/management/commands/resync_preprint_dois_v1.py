import logging
import time

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import Q

from framework.celery_tasks import app
from osf.models import Preprint, Identifier
from osf.models.base import VersionedGuidMixin
from osf.management.commands.sync_doi_metadata import async_request_identifier_update

logger = logging.getLogger(__name__)

# 5-minute pause between rate-limit windows to avoid flooding the Crossref API
# with too many deposit requests in a short period.
RATE_LIMIT_SLEEP = 60 * 5


def get_preprints_needing_v1_doi(provider_id=None):
    content_type = ContentType.objects.get_for_model(Preprint)

    already_versioned_ids = Identifier.objects.filter(
        content_type=content_type,
        category='doi',
        deleted__isnull=True,
        value__contains=VersionedGuidMixin.GUID_VERSION_DELIMITER,
    ).values_list('object_id', flat=True)

    public_query = Q(is_published=True, is_public=True, deleted__isnull=True)
    withdrawn_query = Q(date_withdrawn__isnull=False, ever_public=True)

    qs = Preprint.objects.filter(
        versioned_guids__version=1,
    ).filter(
        public_query | withdrawn_query
    ).exclude(
        id__in=already_versioned_ids
    ).exclude(
        tags__name='qatest',
        tags__system=True,
    ).select_related('provider').distinct()

    if provider_id:
        qs = qs.filter(provider___id=provider_id)

    return qs


def resync_preprint_dois_v1(dry_run=True, batch_size=500, rate_limit=100, provider_id=None):
    preprints_to_update = get_preprints_needing_v1_doi(provider_id=provider_id)

    total = preprints_to_update.count()
    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'{total} preprints need v1 DOI resync'
        + (f' (provider={provider_id})' if provider_id else '')
    )

    if batch_size:
        preprints_iterable = preprints_to_update[:batch_size]
    else:
        preprints_iterable = preprints_to_update.iterator()

    queued = 0
    skipped = 0
    errored = 0
    for record_number, preprint in enumerate(preprints_iterable, 1):
        if not preprint.provider.doi_prefix:
            logger.warning(
                f'Skipping preprint {preprint._id}: '
                f'provider {preprint.provider._id} has no DOI prefix'
            )
            skipped += 1
            continue

        if dry_run:
            logger.info(f'[DRY RUN] Would resync DOI for preprint {preprint._id}')
            queued += 1
            continue

        if rate_limit and not record_number % rate_limit:
            logger.info(f'Rate limit reached at {record_number} preprints, sleeping {RATE_LIMIT_SLEEP}s')
            time.sleep(RATE_LIMIT_SLEEP)

        try:
            async_request_identifier_update.apply_async(kwargs={'preprint_id': preprint._id})
            logger.info(f'Queued DOI resync for preprint {preprint._id}')
            queued += 1
        except Exception:
            logger.exception(f'Failed to queue DOI resync for preprint {preprint._id}')
            errored += 1

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Done: {queued} preprints queued, {skipped} skipped (no DOI prefix), {errored} errored'
    )
    if not dry_run and batch_size:
        logger.info(
            f'Estimated remaining after this batch: ~{max(0, total - queued - skipped - errored)}. '
            f'Re-run this command until 0 preprints remain.'
        )


def get_preprints_needing_unversioned_doi(provider_id=None):
    content_type = ContentType.objects.get_for_model(Preprint)

    already_has_unversioned = Identifier.objects.filter(
        content_type=content_type,
        category='doi_unversioned',
        deleted__isnull=True,
    ).values_list('object_id', flat=True)

    has_versioned_doi = Identifier.objects.filter(
        content_type=content_type,
        category='doi',
        deleted__isnull=True,
        value__contains=VersionedGuidMixin.GUID_VERSION_DELIMITER,
    ).values_list('object_id', flat=True)

    public_query = Q(is_published=True, is_public=True, deleted__isnull=True)
    withdrawn_query = Q(date_withdrawn__isnull=False, ever_public=True)

    qs = Preprint.objects.filter(
        versioned_guids__version=1,
        id__in=has_versioned_doi,
    ).filter(
        public_query | withdrawn_query
    ).exclude(
        id__in=already_has_unversioned
    ).exclude(
        tags__name='qatest',
        tags__system=True,
    ).select_related('provider').distinct()

    if provider_id:
        qs = qs.filter(provider___id=provider_id)

    return qs


def register_missing_unversioned_dois(dry_run=True, batch_size=500, rate_limit=100, provider_id=None):
    preprints_to_update = get_preprints_needing_unversioned_doi(provider_id=provider_id)

    total = preprints_to_update.count()
    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'{total} preprints need unversioned DOI registration'
        + (f' (provider={provider_id})' if provider_id else '')
    )

    if batch_size:
        preprints_iterable = preprints_to_update[:batch_size]
    else:
        preprints_iterable = preprints_to_update.iterator()

    queued = 0
    skipped = 0
    errored = 0
    for record_number, preprint in enumerate(preprints_iterable, 1):
        if not preprint.provider.doi_prefix:
            logger.warning(
                f'Skipping preprint {preprint._id}: '
                f'provider {preprint.provider._id} has no DOI prefix'
            )
            skipped += 1
            continue

        if dry_run:
            logger.info(f'[DRY RUN] Would register unversioned DOI for preprint {preprint._id}')
            queued += 1
            continue

        if rate_limit and not record_number % rate_limit:
            logger.info(f'Rate limit reached at {record_number} preprints, sleeping {RATE_LIMIT_SLEEP}s')
            time.sleep(RATE_LIMIT_SLEEP)

        try:
            async_request_identifier_update.apply_async(kwargs={'preprint_id': preprint._id})
            logger.info(f'Queued unversioned DOI registration for preprint {preprint._id}')
            queued += 1
        except Exception:
            logger.exception(f'Failed to queue unversioned DOI registration for preprint {preprint._id}')
            errored += 1

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Unversioned DOI pass done: {queued} queued, {skipped} skipped, {errored} errored'
    )
    if not dry_run and batch_size:
        logger.info(
            f'Estimated unversioned remaining after this batch: ~{max(0, total - queued - skipped - errored)}. '
            f'Re-run until 0 preprints remain.'
        )


@app.task(name='osf.management.commands.resync_preprint_dois_v1', max_retries=0)
def resync_preprint_dois_v1_task(batch_size=500, rate_limit=100, dry_run=False, provider_id=None):
    resync_preprint_dois_v1(
        dry_run=dry_run,
        batch_size=batch_size,
        rate_limit=rate_limit,
        provider_id=provider_id,
    )
    register_missing_unversioned_dois(
        dry_run=dry_run,
        batch_size=batch_size,
        rate_limit=rate_limit,
        provider_id=provider_id,
    )


class Command(BaseCommand):
    help = (
        'Resync DOIs for version-1 preprints that are missing the versioned DOI suffix (_v1). '
        'Processes preprints in batches and queues Crossref deposit tasks. '
        'IMPORTANT: This command must be run repeatedly until it reports 0 preprints remaining, '
        'as each run only processes a single batch. '
        'Check remaining count with --dry_run before and after each run.'
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry_run',
            action='store_true',
            dest='dry_run',
            help='Log what would be done without submitting to Crossref.',
        )
        parser.add_argument(
            '--batch_size',
            '-b',
            type=int,
            default=500,
            help=(
                'Maximum number of preprints to process per run (default: 500). '
                'The command processes the first N eligible preprints and exits; '
                're-run the command to continue with the next batch.'
            ),
        )
        parser.add_argument(
            '--rate_limit',
            '-r',
            type=int,
            default=100,
            help='Sleep between Crossref submissions every N preprints.',
        )
        parser.add_argument(
            '--provider',
            '-p',
            type=str,
            default=None,
            dest='provider_id',
            help='Restrict to a single provider _id (e.g. socarxiv).',
        )

    def handle(self, *args, **options):
        resync_preprint_dois_v1(
            dry_run=options['dry_run'],
            batch_size=options['batch_size'],
            rate_limit=options['rate_limit'],
            provider_id=options['provider_id'],
        )
