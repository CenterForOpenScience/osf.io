"""
KAKEN data synchronization Celery tasks
"""
import logging
from datetime import timedelta

from framework.celery_tasks import app as celery_app
from django.utils import timezone

from addons.metadata import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def sync_kaken_data(self):
    """
    KAKEN data synchronization task

    This task performs incremental or initial synchronization of KAKEN data
    from the ResourceSync endpoint to Elasticsearch.

    Features:
    - Automatic detection of sync type (initial vs incremental)
    - Resume capability for interrupted syncs
    - Batch processing with configurable limits
    - Automatic retry on failure
    """
    # Check if KAKEN functionality is enabled
    if settings.KAKEN_ELASTIC_URI is None:
        logger.info('KAKEN functionality disabled (KAKEN_ELASTIC_URI is None), skipping sync')
        return

    # Import inside task to avoid circular imports
    from website.app import init_app
    from addons.metadata.suggestions.kaken.client import ResourceSyncClient
    from addons.metadata.suggestions.kaken.transformer import KakenToElasticsearchTransformer
    from addons.metadata.suggestions.kaken.elasticsearch import KakenElasticsearchService
    from addons.metadata.models import KakenSyncLog

    # Initialize Flask app context for database access
    init_app(routes=False)

    logger.info('Starting KAKEN data synchronization task')

    # Initialize services
    client = ResourceSyncClient(
        resourcesync_url=settings.KAKEN_RESOURCESYNC_URL
    )
    transformer = KakenToElasticsearchTransformer()
    es_service = KakenElasticsearchService(
        hosts=[settings.KAKEN_ELASTIC_URI],
        index_name=settings.KAKEN_ELASTIC_INDEX,
        analyzer_config=settings.KAKEN_ELASTIC_ANALYZER_CONFIG,
        **settings.KAKEN_ELASTIC_KWARGS
    )

    # Check if Elasticsearch index exists
    if not es_service.index_exists():
        logger.info('Creating Elasticsearch index for KAKEN data')
        es_service.create_index()

    # Determine sync type and start/resume sync
    last_sync_log = KakenSyncLog.get_last_sync_log()
    if last_sync_log and last_sync_log.status != 'completed':
        logger.info(f'Resuming previous sync (ID: {last_sync_log.id})')
        sync_log = last_sync_log
    else:
        # Determine sync type for new sync
        last_successful_sync = KakenSyncLog.get_last_successful_sync()
        if last_successful_sync is None:
            sync_type = 'initial'
            logger.info('No previous successful sync found, performing initial sync')
        else:
            sync_type = 'incremental'
            logger.info(f'Last successful sync: {last_successful_sync.completed_at}, performing incremental sync')

        sync_log = KakenSyncLog.start_sync(sync_type=sync_type)
        logger.info(f'Started sync log (ID: {sync_log.id}, Type: {sync_type})')

    # Execute synchronization
    from scripts.update_kaken import sync_kaken_data as do_sync
    success = do_sync(client, transformer, es_service, dry_run=False)

    if success:
        logger.info(f'KAKEN data synchronization completed successfully (sync_id: {sync_log.id})')
    else:
        logger.error(f'KAKEN data synchronization failed (sync_id: {sync_log.id})')
        raise Exception('Synchronization failed')


@celery_app.task(ignore_results=True)
def cleanup_old_sync_logs():
    """
    Clean up old synchronization logs

    Keeps only the last 30 days of sync logs to prevent
    database table from growing indefinitely.
    """
    from website.app import init_app
    from addons.metadata.models import KakenSyncLog

    init_app(routes=False)

    cutoff_date = timezone.now() - timedelta(days=30)

    # Keep at least the last 10 successful syncs regardless of age
    successful_syncs = KakenSyncLog.objects.filter(
        status='completed'
    ).order_by('-completed_at')[:10]

    keep_ids = [s.id for s in successful_syncs]

    # Delete old logs except the ones we want to keep
    deleted_count = KakenSyncLog.objects.filter(
        started_at__lt=cutoff_date
    ).exclude(id__in=keep_ids).delete()[0]

    logger.info(f'Deleted {deleted_count} old KAKEN sync logs')
