import logging
from django.db import transaction
from django.utils import timezone
from django.core.management.base import BaseCommand
from framework.celery_tasks import app as celery_app

from osf.models import QuickFilesNode
from osf.management.commands.transfer_quickfiles_to_projects import paginated_progressbar
logger = logging.getLogger(__name__)


@celery_app.task(name='management.commands.delete_legacy_quickfiles_nodes')
def delete_legacy_quickfiles_nodes(page):
    for node in page:
        node.is_deleted = True
        node.deleted = timezone.now()
        node.save()


def delete_quickfiles(batch_size=1000, page_size=1000, dry_run=False):
    with transaction.atomic():

        paginated_progressbar(
            QuickFilesNode.objects.all()[:batch_size],
            lambda page: delete_legacy_quickfiles_nodes(page),
            page_size=page_size,
            dry_run=dry_run
        )
        logger.info(f'All Quickfiles deleted')


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
            required=False,
        )
        parser.add_argument(
            '--page_size',
            type=int,
            help='how many many query items should be in a page?',
            required=False,
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', 1000)
        batch_size = options.get('batch_size', 1000)
        page_size = options.get('page_size', 1000)
        delete_quickfiles(dry_run, batch_size, page_size)
