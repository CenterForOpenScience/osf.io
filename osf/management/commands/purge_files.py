import logging

from django.utils import timezone

from framework.celery_tasks import app as celery_app
from website.app import setup_django
setup_django()
from osf.models import Registration
from addons.osfstorage.models import TrashedFileNode
from django.core.management.base import BaseCommand
from osf.utils.workflows import RegistrationModerationStates
from website.settings import GCS_CREDS, PURGE_DELTA
from google.cloud.storage.client import Client
from google.oauth2.service_account import Credentials


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def mark_withdrawn_files_as_deleted(dry_run=False):
    for node in Registration.objects.filter(moderation_state=RegistrationModerationStates.WITHDRAWN.db_name):
        for file in node.files.all():
            if not dry_run:
                file.delete()


def purge_deleted_withdrawn_files(dry_run=False):
    deleted_file_ids_on_withdrawn_node = Registration.objects.filter(
        moderation_state=RegistrationModerationStates.WITHDRAWN.db_name,
        files__deleted__lte=timezone.now() - PURGE_DELTA
    ).values_list('files__id', flat=True).distinct()

    creds = Credentials.from_service_account_file(GCS_CREDS)
    client = Client(credentials=creds)
    for file in TrashedFileNode.objects.filter(id__in=deleted_file_ids_on_withdrawn_node):
        if not dry_run:
            file._purge(client=client)


@celery_app.task(name='management.commands.purge_files')
def main(dry_run=False):
    """
    This script purges files that are deleted after being withdrawn 30 days.
    """
    if dry_run:
        logger.info('This is a dry run; no files will be purged or marked as deleted.')

    mark_withdrawn_files_as_deleted(dry_run)
    purge_deleted_withdrawn_files(dry_run)


class Command(BaseCommand):
    help = '''
        This script purges files that are deleted after being withdrawn 30 days.
    '''

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    # Management command handler
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', True)
        main(dry_run=dry_run)
