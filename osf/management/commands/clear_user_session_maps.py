import logging
import django
django.setup()

from framework.celery_tasks import app as celery_app
from osf.models import UserSessionMap
from django.utils import timezone

logger = logging.getLogger(__name__)
django.setup()

from django.core.management.base import BaseCommand


@celery_app.task(name='osf.management.commands.clear_user_session_maps')
def clear_user_session_maps(dry_run=False):
    current_time = timezone.now()
    old_session_maps = UserSessionMap.objects.filter(expire_date__lt=current_time)
    count = old_session_maps.count()
    logger.info(f'Preparing to delete UserSessionMap objects with expire_date > {current_time}')
    if not dry_run:
        old_session_maps.delete()
        logger.info(f'Successfully deleted {count} objects')
    else:
        logger.warn('Dry run mode, nothing is deleted')

class Command(BaseCommand):
    """
    Runs everyday to clear UserSessionMap objects that expires today.
    """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='dry run mode',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        clear_user_session_maps(dry_run=dry_run)
