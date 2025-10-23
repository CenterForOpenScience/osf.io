"""
KAKEN ResourceSync Client Script

Usage:
  python3 -m scripts.update_kaken            # Perform actual synchronization
  python3 -m scripts.update_kaken --dry-run  # Test synchronization (no writes)
  python3 -m scripts.update_kaken -v         # Verbose logging
"""

import argparse
import sys
import logging
import django
from collections import Counter
from datetime import timezone
from dateutil.parser import parse as parse_datetime
from scripts import utils as script_utils

django.setup()

from website.app import init_app
from addons.metadata.suggestions.kaken.client import ResourceSyncClient
from addons.metadata.suggestions.kaken.transformer import KakenToElasticsearchTransformer
from addons.metadata.suggestions.kaken.elasticsearch import KakenElasticsearchService
from addons.metadata.models import KakenSyncLog


logger = logging.getLogger(__name__)


class ChangeStats:
    __slots__ = ('applied', 'skipped')

    def __init__(self):
        self.applied = Counter()
        self.skipped = Counter()

    def record_applied(self, action):
        self.applied[action] += 1

    def record_skipped(self, action):
        self.skipped[action] += 1

    def applied_count(self, action):
        return self.applied.get(action, 0)

    def skipped_count(self, action):
        return self.skipped.get(action, 0)

    def merge(self, other: 'ChangeStats'):
        self.applied += other.applied
        self.skipped += other.skipped

    def total_checked(self):
        return sum(self.applied.values())


def _normalize_datetime(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _should_apply_change(item_lastmod_dt, existing_doc, doc_label):
    if item_lastmod_dt is None:
        raise ValueError(f'Missing item lastmod for {doc_label}')

    if not existing_doc:
        return True

    existing_last = existing_doc.get('_last_updated')
    if not existing_last:
        return True

    try:
        existing_dt = parse_datetime(existing_last)
    except (ValueError, TypeError):
        logger.warning('Invalid _last_updated for %s: %s', doc_label, existing_last, exc_info=True)
        return True

    new_norm = _normalize_datetime(item_lastmod_dt)
    existing_norm = _normalize_datetime(existing_dt)
    if not new_norm or not existing_norm:
        return True
    return new_norm > existing_norm


def sync_kaken_data(client: ResourceSyncClient, transformer: KakenToElasticsearchTransformer,
                   es_service: KakenElasticsearchService, dry_run: bool = False,
                   limit: int = None) -> bool:
    """Run KAKEN synchronization. Returns True on success, False otherwise.

    Args:
        client: ResourceSync client
        transformer: Transformer
        es_service: ES service
        dry_run: If True, analyze only
        limit: Optional max number of documents to process this run
    """
    banner = 'Performing dry run analysis of KAKEN data synchronization...' if dry_run else 'Starting KAKEN data synchronization...'
    print(banner)
    print(f'ResourceSync URL: {client.resourcesync_url}')

    # State
    sync_log = None
    sync_type = 'initial'
    processed_records = 0
    errors_count = 0
    overall_stats = ChangeStats()

    from addons.metadata import settings
    max_documents = limit if (isinstance(limit, int) and limit > 0) else settings.KAKEN_SYNC_MAX_DOCUMENTS_PER_EXECUTION

    try:
        # Resume or start new
        last_sync_log = KakenSyncLog.get_last_sync_log()
        if last_sync_log and last_sync_log.status != 'completed':
            print(f'Resuming previous sync (ID: {last_sync_log.id})')
            sync_log = last_sync_log
            sync_type = sync_log.sync_type
            errors_count = sync_log.errors_count or 0
        else:
            last_successful = KakenSyncLog.get_last_successful_sync()
            if last_successful is None:
                sync_type = 'initial'
                print('No previous sync found - performing initial sync')
            else:
                sync_type = 'incremental'
                print(f'Last successful sync: {last_successful.completed_at} - performing incremental sync')
            if not dry_run:
                sync_log = KakenSyncLog.start_sync(sync_type=sync_type)
                print(f'Started sync log (ID: {sync_log.id}, Type: {sync_type})')

        # Ensure index exists
        if not dry_run and not es_service.index_exists():
            print('Creating Elasticsearch index for KAKEN data...')
            es_service.create_index()
            print('Index created successfully')

        # Capability lists
        capabilities = client.get_capability_list()
        resourcelists = capabilities.get('resourcelists', [])
        changelists = capabilities.get('changelists', [])

        if sync_type == 'initial':
            print(f'\nProcessing {len(resourcelists)} resource lists...')
            start_index = sync_log.current_resourcelist_index if sync_log else 0
            for i in range(start_index, len(resourcelists)):
                info = resourcelists[i]
                url = info['url']
                lastmod = info.get('lastmod')
                print(f'\n[{i+1}/{len(resourcelists)}] Processing resource list: {url}')
                if lastmod:
                    print(f'  Resource list lastmod: {lastmod}')
                if sync_log:
                    sync_log.current_resourcelist_index = i
                    sync_log.current_resourcelist_url = url
                    sync_log.save()

                urls = list(client.process_resource_list(url))
                print(f'  Counting total documents... {len(urls)} documents found')
                start_progress = sync_log.current_resourcelist_progress if sync_log else 0
                if sync_log:
                    sync_log.total_documents_in_batch = len(urls)
                    sync_log.documents_processed_in_batch = start_progress
                    sync_log.save()

                batch = []
                local_stats = ChangeStats()
                items_seen = 0

                for j, (json_url, item_lastmod) in enumerate(urls):
                    if j < start_progress:
                        continue
                    if processed_records >= max_documents:
                        print(f'\nReached maximum documents per execution ({max_documents}), stopping...')
                        if not dry_run and batch:
                            ts = lastmod.isoformat() if lastmod else None
                            result = es_service.bulk_index(batch, update_timestamp=ts)
                            errors_count += result['errors']
                        if sync_log:
                            sync_log.current_resourcelist_progress = j
                            sync_log.documents_processed_in_batch = start_progress + items_seen
                            sync_log.save()
                        overall_stats.merge(local_stats)
                        return True

                    items_seen += 1

                    if not item_lastmod:
                        raise ValueError('Missing lastmod for resource list item')

                    doc_id = es_service.doc_id_from_url(json_url)
                    if not doc_id:
                        raise ValueError('Failed to derive document ID from resource list URL')

                    existing = es_service.get_researcher_by_id(doc_id)
                    apply_change = _should_apply_change(item_lastmod, existing, json_url)

                    if dry_run:
                        if apply_change:
                            action = 'update' if existing else 'create'
                            local_stats.record_applied(action)
                        else:
                            local_stats.record_skipped('update')
                        print(f'\r  Progress: [{j+1}/{len(urls)}]', end='', flush=True)
                    else:
                        if apply_change:
                            data = client.fetch_researcher_data(json_url)
                            doc = transformer.transform_researcher(data)
                            doc['_last_updated'] = item_lastmod.isoformat()
                            source_url = doc.get('_source_url') or json_url
                            if not source_url:
                                raise ValueError('Missing _source_url for document ID derivation')
                            doc['_source_url'] = source_url
                            batch.append(doc)
                            action = 'update' if existing else 'create'
                            local_stats.record_applied(action)
                            processed_records += 1
                        else:
                            local_stats.record_skipped('update')

                    if sync_log:
                        sync_log.current_resourcelist_progress = j + 1
                        sync_log.documents_processed_in_batch = start_progress + items_seen
                        if items_seen % 50 == 0:
                            sync_log.save()

                    if not dry_run and apply_change and len(batch) >= 100:
                        result = es_service.bulk_index(batch)
                        errors_count += result['errors']
                        if result['errors'] > 0:
                            print(f"WARNING: {result['errors']} errors in batch", file=sys.stderr)
                        batch = []
                        print(f'  Processed {start_progress + items_seen}/{len(urls)} items from this list')

                if not dry_run and batch:
                    result = es_service.bulk_index(batch)
                    errors_count += result['errors']

                total_items = max(len(urls) - start_progress, 0)
                summary = f"  Completed resource list {i+1}: {items_seen}/{total_items} {'checked' if dry_run else 'records'}"
                if dry_run:
                    summary += (
                        f', would_update={local_stats.applied_count("update")}, '
                        f'would_create={local_stats.applied_count("create")}, '
                        f'skipped_updates={local_stats.skipped_count("update")}'
                    )
                else:
                    summary += (
                        f', applied_updates={local_stats.applied_count("update")}, '
                        f'applied_creates={local_stats.applied_count("create")}, '
                        f'skipped_updates={local_stats.skipped_count("update")}'
                    )
                print(summary)
                if sync_log:
                    sync_log.current_resourcelist_progress = 0
                    sync_log.documents_processed_in_batch = 0
                    sync_log.total_documents_in_batch = 0
                    sync_log.update_progress(processed_records=processed_records, errors_count=errors_count)
                    sync_log.save()

                overall_stats.merge(local_stats)

        else:
            print(f'\nProcessing {len(changelists)} change lists...')
            last_success = KakenSyncLog.get_last_successful_sync()
            start_index = sync_log.current_changelist_index if sync_log else 0
            for i in range(start_index, len(changelists)):
                info = changelists[i]
                url = info['url']
                lastmod = info.get('lastmod')
                print(f'\n[{i+1}/{len(changelists)}] Processing change list: {url}')
                if lastmod:
                    print(f'  Change list lastmod: {lastmod}')
                if sync_log:
                    sync_log.current_changelist_index = i
                    sync_log.current_changelist_url = url
                    sync_log.save()

                changes = list(client.process_change_list(url))
                print(f'  Counting total changes... {len(changes)} changes found')
                start_progress = sync_log.current_changelist_progress if sync_log else 0
                if sync_log:
                    sync_log.total_documents_in_batch = len(changes)
                    sync_log.documents_processed_in_batch = start_progress
                    sync_log.save()

                batch = []
                local_stats = ChangeStats()
                items_seen = 0
                for j, (action, json_url, item_lastmod) in enumerate(changes):
                    if j < start_progress:
                        continue
                    if processed_records >= max_documents:
                        print(f'\nReached maximum documents per execution ({max_documents}), stopping...')
                        if not dry_run and batch:
                            result = es_service.bulk_index(batch)
                            errors_count += result['errors']
                        if sync_log:
                            sync_log.current_changelist_progress = j
                            sync_log.documents_processed_in_batch = start_progress + items_seen
                            sync_log.save()
                        overall_stats.merge(local_stats)
                        return True

                    items_seen += 1

                    if action == 'deleted':
                        doc_id = es_service.doc_id_from_url(json_url)
                        if not doc_id:
                            raise ValueError('Failed to derive document ID for deletion action')
                        existing = es_service.get_researcher_by_id(doc_id)
                        apply_change = _should_apply_change(item_lastmod, existing, json_url)
                        if dry_run:
                            if apply_change:
                                local_stats.record_applied('delete')
                            else:
                                local_stats.record_skipped('delete')
                            print(f'\r  Progress: [{j+1}/{len(changes)}]', end='', flush=True)
                        else:
                            if not apply_change:
                                local_stats.record_skipped('delete')
                            else:
                                timestamp = item_lastmod.isoformat() if item_lastmod else None
                                if es_service.soft_delete_researcher(doc_id, timestamp):
                                    processed_records += 1
                                    local_stats.record_applied('delete')
                                else:
                                    errors_count += 1
                                    local_stats.record_skipped('delete')
                        if sync_log:
                            sync_log.current_changelist_progress = j + 1
                            sync_log.documents_processed_in_batch = start_progress + items_seen
                            if items_seen % 50 == 0:
                                sync_log.save()
                        continue

                    if not item_lastmod:
                        raise ValueError('Missing lastmod for change list item')

                    doc_id = es_service.doc_id_from_url(json_url)
                    if not doc_id:
                        raise ValueError('Failed to derive document ID from change list URL')

                    existing = es_service.get_researcher_by_id(doc_id)
                    apply_change = _should_apply_change(item_lastmod, existing, json_url)

                    if dry_run:
                        if apply_change:
                            action_name = 'update' if existing else 'create'
                            local_stats.record_applied(action_name)
                        else:
                            local_stats.record_skipped('update')
                        print(f'\r  Progress: [{j+1}/{len(changes)}]', end='', flush=True)
                        if sync_log:
                            sync_log.current_changelist_progress = j + 1
                            sync_log.documents_processed_in_batch = start_progress + items_seen
                            if items_seen % 50 == 0:
                                sync_log.save()
                        continue

                    if not apply_change:
                        local_stats.record_skipped('update')
                        if sync_log:
                            sync_log.current_changelist_progress = j + 1
                            sync_log.documents_processed_in_batch = start_progress + items_seen
                            if items_seen % 50 == 0:
                                sync_log.save()
                        continue

                    data = client.fetch_researcher_data(json_url)
                    doc = transformer.transform_researcher(data)
                    doc['_last_updated'] = item_lastmod.isoformat() if item_lastmod else None
                    source_url = doc.get('_source_url') or json_url
                    if not source_url:
                        raise ValueError('Missing _source_url for document ID derivation')
                    doc['_source_url'] = source_url
                    batch.append(doc)
                    processed_records += 1
                    action_name = 'update' if existing else 'create'
                    local_stats.record_applied(action_name)

                    if sync_log:
                        sync_log.current_changelist_progress = j + 1
                        sync_log.documents_processed_in_batch = start_progress + items_seen
                        if items_seen % 50 == 0:
                            sync_log.save()

                    if len(batch) >= 100:
                        result = es_service.bulk_index(batch)
                        errors_count += result['errors']
                        batch = []
                        print(f'  Processed {start_progress + items_seen}/{len(changes)} items from this list')

                if not dry_run and batch:
                    result = es_service.bulk_index(batch)
                    errors_count += result['errors']

                total_changes = max(len(changes) - start_progress, 0)
                summary = f"  Completed change list {i+1}: {items_seen}/{total_changes} {'checked' if dry_run else 'entries'}"
                if dry_run:
                    summary += (
                        f', would_update={local_stats.applied_count("update")}, '
                        f'would_create={local_stats.applied_count("create")}, '
                        f'would_delete={local_stats.applied_count("delete")}, '
                        f'skipped_updates={local_stats.skipped_count("update")}, '
                        f'skipped_deletes={local_stats.skipped_count("delete")}'
                    )
                else:
                    summary += (
                        f', applied_updates={local_stats.applied_count("update")}, '
                        f'applied_creates={local_stats.applied_count("create")}, '
                        f'applied_deletes={local_stats.applied_count("delete")}, '
                        f'skipped_updates={local_stats.skipped_count("update")}, '
                        f'skipped_deletes={local_stats.skipped_count("delete")}'
                    )
                print(summary)
                if sync_log:
                    sync_log.current_changelist_progress = 0
                    sync_log.documents_processed_in_batch = 0
                    sync_log.total_documents_in_batch = 0
                    sync_log.update_progress(processed_records=processed_records, errors_count=errors_count)
                    sync_log.save()

                overall_stats.merge(local_stats)

        # Finalize
        if not dry_run:
            es_service.refresh_index()
        stats = es_service.get_index_stats()
        total_docs = stats.get('_all', {}).get('total', {}).get('docs', {}).get('count', 0) if stats else 0
        if sync_log:
            sync_log.complete_sync(processed_records=processed_records, errors_count=errors_count, total_records=total_docs)
        if dry_run:
            checked = overall_stats.total_checked()
            print(
                f'Dry run completed: {sync_type}, '
                f'checked={checked}, '
                f'would_update={overall_stats.applied_count("update")}, '
                f'would_create={overall_stats.applied_count("create")}, '
                f'would_delete={overall_stats.applied_count("delete")}, '
                f'errors={errors_count}, total_docs={total_docs}'
            )
        else:
            print(f'Sync completed: {sync_type}, processed={processed_records}, errors={errors_count}, total_docs={total_docs}, duration={sync_log.duration}')
        return errors_count == 0
    except Exception:
        logger.exception('Sync failed')
        if sync_log:
            sync_log.fail_sync(error_details='Sync failed (see logs)', processed_records=processed_records, errors_count=errors_count)
        return False


def main():
    """Main CLI entry point"""
    init_app(routes=False)

    parser = argparse.ArgumentParser(description='KAKEN ResourceSync Client CLI')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run of synchronization process')
    parser.add_argument('--url', type=str, help='Override ResourceSync URL')
    parser.add_argument('--timeout', type=int, default=60, help='Request timeout in seconds')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--limit', '-l', type=int, help='Limit number of documents to process for this run')
    parser.add_argument('--force-recreate', action='store_true', help='Clear sync state and recreate ES index, then run initial sync')
    parser.add_argument('--yes', action='store_true', help='Assume yes for confirmation prompts')

    args = parser.parse_args()

    # Configure logging
    script_utils.add_file_logger(logger, __file__)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)

    # Initialize components
    from addons.metadata import settings
    if settings.KAKEN_ELASTIC_URI is None:
        print('KAKEN functionality disabled (KAKEN_ELASTIC_URI is None)')
        print('Please configure KAKEN_ELASTIC_URI in settings to enable KAKEN synchronization')
        sys.exit(1)

    client = ResourceSyncClient(
        resourcesync_url=args.url or settings.KAKEN_RESOURCESYNC_URL,
        timeout=args.timeout
    )
    transformer = KakenToElasticsearchTransformer()
    es_service = KakenElasticsearchService(
        hosts=[settings.KAKEN_ELASTIC_URI],
        index_name=settings.KAKEN_ELASTIC_INDEX,
        analyzer_config=settings.KAKEN_ELASTIC_ANALYZER_CONFIG,
        **settings.KAKEN_ELASTIC_KWARGS
    )

    # Destructive reset (state + index)
    if args.force_recreate:
        if args.dry_run:
            print('ERROR: --force-recreate cannot be combined with --dry-run', file=sys.stderr)
            sys.exit(1)
        if not args.yes:
            try:
                confirm = input('This will CLEAR KakenSyncLog and RECREATE the ES index. Type "yes" to continue: ')
            except EOFError:
                confirm = ''
            if confirm.strip().lower() != 'yes':
                print('Aborted by user')
                sys.exit(1)
        # Clear sync logs
        deleted = KakenSyncLog.objects.all().count()
        KakenSyncLog.objects.all().delete()
        print(f'Cleared KakenSyncLog: {deleted} records')
        # Recreate index
        es_service.create_index(delete_existing=True)
        print(f'Recreated index: {settings.KAKEN_ELASTIC_INDEX}')

    success = True
    try:
        success = sync_kaken_data(client, transformer, es_service, dry_run=args.dry_run, limit=args.limit)
    finally:
        client.close()
        es_service.close()

    if success:
        sys.exit(0)
    else:
        if args.dry_run:
            print('ERROR: Dry run failed', file=sys.stderr)
        else:
            print('ERROR: Data synchronization failed', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
