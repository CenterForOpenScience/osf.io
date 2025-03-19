import logging
from django.db import transaction
from django.utils import timezone
from django.core.management.base import BaseCommand
from framework import sentry
from framework.celery_tasks import app as celery_app

from osf.models import QuickFilesNode, Node
logger = logging.getLogger(__name__)


@celery_app.task(name='osf.management.commands.delete_legacy_quickfiles_nodes')
def delete_quickfiles(batch_size=1000, dry_run=False):
    """
    This is a periodic command to sunset our Quickfiles feature and can be safely deleted after
    Quickfiles are all marked as deleted.
    """
    with transaction.atomic():
        i = 0
        for i, node in enumerate(QuickFilesNode.objects.all()[:batch_size]):
            node.is_deleted = True
            node.deleted = timezone.now()
            node.recast(Node._typedmodels_type)
            node.save()

        logger.info(f'{i} Quickfiles deleted')

        if dry_run:
            raise RuntimeError('dry run rolling back changes')

    if not QuickFilesNode.objects.exists():
        sentry.log_message('Clean-up complete, none more QuickFilesNode delete this task.')


class Command(BaseCommand):
    """
    Deletes unused legacy Quickfiles.
    """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
            required=False,
        )
        parser.add_argument(
            '--batch_size',
            type=int,
            help='how many many Quickfiles are we deleting tonight?',
            required=True,
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        batch_size = options.get('batch_size', 1000)
        delete_quickfiles(batch_size, dry_run)
