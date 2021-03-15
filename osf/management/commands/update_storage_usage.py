import datetime
import logging

from osf.models import AbstractNode
from api.caching.tasks import update_storage_usage_cache

from django.core.management.base import BaseCommand
from datetime import timezone
from framework.celery_tasks import app as celery_app
from django.db import transaction

logger = logging.getLogger(__name__)

DAYS = 1

@celery_app.task(name='management.commands.update_storage_usage')
def update_storage_usage(dry_run=False, days=DAYS):
    with transaction.atomic():
        modified_limit = timezone.now() - timezone.timedelta(days=days)
        recently_modified = AbstractNode.objects.filter(modified__gt=modified_limit)
        for modified_node in recently_modified:
            file_op_occurred = modified_node.logs.filter(action__contains='file', created__gt=modified_limit).exists()
            if not modified_node.is_quickfiles and file_op_occurred:
                update_storage_usage_cache(modified_node.id, modified_node._id)

        if dry_run:
            raise RuntimeError('Dry run -- Transaction rolled back')

class Command(BaseCommand):
    help = '''Updates the storage usage for all nodes modified in the last day'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Run script but do not commit',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=DAYS,
            help='How many days to backfill',
        )

    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))
        logger.debug(options)

        dry_run = options['dry_run']
        days = options['days']

        if dry_run:
            logger.info('DRY RUN')

        update_storage_usage(dry_run, days)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
