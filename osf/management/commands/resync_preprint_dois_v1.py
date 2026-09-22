import logging
from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from framework.celery_tasks import app
from osf.models import Preprint, Identifier
from osf.models.base import VersionedGuidMixin
from osf.management.commands.sync_doi_metadata import async_request_identifier_update
from website import settings

logger = logging.getLogger(__name__)


@dataclass
class ResyncPassResult:
    total: int
    queued: int
    skipped: int
    errored: int

    @property
    def remaining(self):
        # Preprints that still need this pass after accounting for what was just queued.
        return max(0, self.total - self.queued)


def get_in_flight_doi_resync_count():
    # Preprints with a DOI resync request dispatched to Crossref that hasn't been confirmed or gone stale.
    cutoff = timezone.now() - settings.PREPRINT_DOI_RESYNC_INFLIGHT_TIMEOUT
    return Preprint.objects.filter(doi_resync_queued_at__gte=cutoff).count()


def get_available_doi_resync_capacity():
    return max(0, settings.PREPRINT_DOI_RESYNC_MAX_IN_FLIGHT - get_in_flight_doi_resync_count())


def _not_in_flight_query():
    cutoff = timezone.now() - settings.PREPRINT_DOI_RESYNC_INFLIGHT_TIMEOUT
    return Q(doi_resync_queued_at__isnull=True) | Q(doi_resync_queued_at__lt=cutoff)


def _batch_for_pass(preprints_to_update, dry_run, batch_size, capacity):
    """Slice the queryset for one pass.

    A dry run just previews the backlog and ignores in-flight capacity. A live run is
    capped by both `batch_size` and the capacity which is left in the shared in-flight  for this tick.
    """
    if dry_run:
        return preprints_to_update[:batch_size] if batch_size else preprints_to_update.iterator()

    if capacity is None:
        capacity = get_available_doi_resync_capacity()
    effective_batch_size = min(batch_size, capacity) if batch_size else capacity
    return preprints_to_update[:effective_batch_size] if effective_batch_size else []


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
    ).filter(
        _not_in_flight_query()
    ).exclude(
        id__in=already_versioned_ids
    ).exclude(
        tags__name='qatest',
        tags__system=True,
    ).select_related('provider').distinct().order_by('id')

    if provider_id:
        qs = qs.filter(provider___id=provider_id)

    return qs


def resync_preprint_dois_v1(dry_run=True, batch_size=1000, provider_id=None, capacity=None):
    preprints_to_update = get_preprints_needing_v1_doi(provider_id=provider_id)

    total = preprints_to_update.count()
    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'{total} preprints need v1 DOI resync'
        + (f' (provider={provider_id})' if provider_id else '')
    )

    preprints_iterable = _batch_for_pass(preprints_to_update, dry_run, batch_size, capacity)

    queued = 0
    skipped = 0
    errored = 0
    for preprint in preprints_iterable:
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

        try:
            async_request_identifier_update.apply_async(kwargs={'preprint_id': preprint._id})
            Preprint.objects.filter(id=preprint.id).update(doi_resync_queued_at=timezone.now())
            logger.info(f'Queued DOI resync for preprint {preprint._id}')
            queued += 1
        except Exception:
            logger.exception(f'Failed to queue DOI resync for preprint {preprint._id}')
            errored += 1

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Done: {queued} preprints queued, {skipped} skipped (no DOI prefix), {errored} errored'
    )
    result = ResyncPassResult(total=total, queued=queued, skipped=skipped, errored=errored)
    if not dry_run and batch_size:
        logger.info(
            f'Estimated remaining after this batch: ~{result.remaining}. '
            f'Re-run this command until 0 preprints remain.'
        )
    return result


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
    ).filter(
        _not_in_flight_query()
    ).exclude(
        id__in=already_has_unversioned
    ).exclude(
        tags__name='qatest',
        tags__system=True,
    ).select_related('provider').distinct().order_by('id')

    if provider_id:
        qs = qs.filter(provider___id=provider_id)

    return qs


def register_missing_unversioned_dois(dry_run=True, batch_size=1000, provider_id=None, capacity=None):
    preprints_to_update = get_preprints_needing_unversioned_doi(provider_id=provider_id)

    total = preprints_to_update.count()
    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'{total} preprints need unversioned DOI registration'
        + (f' (provider={provider_id})' if provider_id else '')
    )

    preprints_iterable = _batch_for_pass(preprints_to_update, dry_run, batch_size, capacity)

    queued = 0
    skipped = 0
    errored = 0
    for preprint in preprints_iterable:
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

        try:
            async_request_identifier_update.apply_async(kwargs={'preprint_id': preprint._id})
            Preprint.objects.filter(id=preprint.id).update(doi_resync_queued_at=timezone.now())
            logger.info(f'Queued unversioned DOI registration for preprint {preprint._id}')
            queued += 1
        except Exception:
            logger.exception(f'Failed to queue unversioned DOI registration for preprint {preprint._id}')
            errored += 1

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Unversioned DOI pass done: {queued} queued, {skipped} skipped, {errored} errored'
    )
    result = ResyncPassResult(total=total, queued=queued, skipped=skipped, errored=errored)
    if not dry_run and batch_size:
        logger.info(
            f'Estimated unversioned remaining after this batch: ~{result.remaining}. '
            f'Re-run until 0 preprints remain.'
        )
    return result


@app.task(bind=True, name='osf.management.commands.resync_preprint_dois_v1', max_retries=0)
def resync_preprint_dois_v1_task(self, batch_size=1000, dry_run=False, provider_id=None):
    capacity = None if dry_run else get_available_doi_resync_capacity()

    v1_result = resync_preprint_dois_v1(
        dry_run=dry_run,
        batch_size=batch_size,
        provider_id=provider_id,
        capacity=capacity,
    )
    if capacity is not None:
        capacity = max(0, capacity - v1_result.queued)

    unversioned_result = register_missing_unversioned_dois(
        dry_run=dry_run,
        batch_size=batch_size,
        provider_id=provider_id,
        capacity=capacity,
    )

    if not dry_run and (v1_result.remaining > 0 or unversioned_result.remaining > 0):
        logger.info(
            f'Rescheduling DOI resync dispatcher in '
            f'{settings.PREPRINT_DOI_RESYNC_DISPATCH_INTERVAL} '
            f'({v1_result.remaining} v1 + {unversioned_result.remaining} unversioned remaining)'
        )
        self.apply_async(
            kwargs={
                'batch_size': batch_size,
                'dry_run': dry_run,
                'provider_id': provider_id,
            },
            countdown=settings.PREPRINT_DOI_RESYNC_DISPATCH_INTERVAL.total_seconds(),
        )


class Command(BaseCommand):
    help = (
        'Resync DOIs for version-1 preprints that are missing the versioned DOI suffix (_v1), '
        'and register missing unversioned DOIs. '
        'With --dry_run, previews the backlog synchronously and exits. '
        'Otherwise, starts the resync_preprint_dois_v1_task dispatcher once: it queues an initial '
        'batch (bounded by --batch_size and the shared in-flight capacity, see '
        'PREPRINT_DOI_RESYNC_MAX_IN_FLIGHT) and self-reschedules every '
        'PREPRINT_DOI_RESYNC_DISPATCH_INTERVAL until the backlog is drained, then stops on its '
        'own -- no need to re-run this command.'
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
            default=1000,
            help='Maximum number of preprints to process per dispatch tick (default: 1000).',
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
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        provider_id = options['provider_id']

        if dry_run:
            # Synchronous preview of both passes; nothing gets queued or dispatched.
            resync_preprint_dois_v1(dry_run=True, batch_size=batch_size, provider_id=provider_id)
            register_missing_unversioned_dois(dry_run=True, batch_size=batch_size, provider_id=provider_id)
            return

        resync_preprint_dois_v1_task.apply_async(
            kwargs={
                'batch_size': batch_size,
                'dry_run': False,
                'provider_id': provider_id,
            },
        )
        self.stdout.write(
            'Started the DOI resync dispatcher. It will self-reschedule on its own until the '
            'backlog is drained -- no need to re-run this command. Check logs/Sentry for progress.'
        )
