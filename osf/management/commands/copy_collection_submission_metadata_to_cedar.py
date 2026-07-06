import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import CollectionSubmission

logger = logging.getLogger(__name__)


def copy_collection_submission_metadata_to_cedar(dry_run=False, batch_size=100, provider_id=None):
    qs = CollectionSubmission.objects.filter(
        collection__provider__required_metadata_template__isnull=False,
    ).select_related(
        'guid',
        'collection__provider__required_metadata_template',
    )

    if provider_id:
        qs = qs.filter(collection__provider___id=provider_id)

    total = qs.count()
    logger.info(f'{"[DRY RUN] " if dry_run else ""}Found {total} collection submissions to process')

    processed = errors = 0
    succeeded = []
    failed = []
    for submission in qs.iterator(chunk_size=batch_size):
        if dry_run:
            logger.info(f'[DRY RUN] Would sync cedar metadata for submission {submission._id}')
            continue
        try:
            record = submission.sync_cedar_metadata()
            succeeded.append((
                submission.guid._id,
                submission.collection._id,
                record._id,
                record.template.cedar_id,
            ))
            processed += 1
        except Exception as e:
            logger.error(f'Failed to sync cedar metadata for submission {submission._id}: {e}')
            template = submission.collection.provider.required_metadata_template
            failed.append((
                submission.guid._id,
                submission.collection._id,
                template.cedar_id,
                e,
            ))
            errors += 1

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Done. Processed {processed}/{total} submissions'
        f'{f", {errors} error(s)" if errors else ""}'
    )
    if succeeded:
        logger.info('Successfully synced (node_guid, collection_id, cedar_record_id, cedar_template_id):')
        for node_guid, collection_id, record_id, template_cedar_id in succeeded:
            logger.info(f'  node={node_guid}, collection={collection_id}, record={record_id}, template={template_cedar_id}')
    if failed:
        logger.info('Failed (node_guid, collection_id, cedar_template_id):')
        for node_guid, collection_id, template_cedar_id, exc in failed:
            logger.info(f'  node={node_guid}, collection={collection_id}, template={template_cedar_id}, error={exc}')


class Command(BaseCommand):
    help = 'Copy CollectionSubmission custom metadata fields to CedarMetadataRecord for providers with a required cedar template.'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Preview what would be synced without making any changes',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            dest='batch_size',
            help='Number of submissions to process per iteration (default: 100)',
        )
        parser.add_argument(
            '--provider',
            type=str,
            dest='provider_id',
            help='Optional collection provider _id to limit processing to a single provider',
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            copy_collection_submission_metadata_to_cedar(
                dry_run=options['dry_run'],
                batch_size=options['batch_size'],
                provider_id=options.get('provider_id'),
            )
