import logging
import django
django.setup()

from framework.celery_tasks import app as celery_app
from osf.models import Registration
from website import settings
from osf.utils.requests import requests_retry_session

logger = logging.getLogger(__name__)
django.setup()

from django.core.management.base import BaseCommand


@celery_app.task(name='osf.management.commands.archive_registrations_on_IA')
def archive_registrations_on_IA(dry_run=False):
    registrations = Registration.objects.filter(IA_url__isnull=True, is_public=True)[:100]

    logger.info(f'{registrations.count()} to be archived in batch')

    for registration in registrations:
        if not dry_run:
            logger.info(f'archiving {registration._id}')
            requests_retry_session().post(f'{settings.OSF_PIGEON_URL}archive/{registration._id}')
        else:
            logger.info(f'DRY RUN for archiving {registration._id}')

class Command(BaseCommand):
    """
    Nightly task to take a number of Registrations and gradually archive them on archive.org via our archiving service
    osf-pigeon
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        archive_registrations_on_IA(dry_run=dry_run)
