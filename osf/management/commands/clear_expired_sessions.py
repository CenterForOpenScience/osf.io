from importlib import import_module
import logging

import django
from django.conf import settings as django_conf_settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from osf.models import UserSessionMap

django.setup()
SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore
logger = logging.getLogger(__name__)


@celery_app.task(name="osf.management.commands.clear_expired_sessions")
def clear_expired_sessions(dry_run=False):
    current_time = timezone.now()
    old_session_maps = UserSessionMap.objects.filter(
        expire_date__lt=current_time
    )
    count = old_session_maps.count()
    logger.info(
        f"Preparing to clear expired Django Sessions and remove {count} expired UserSessionMap objects."
    )
    if not dry_run:
        logger.info("Clearing expired Django Sessions ...")
        SessionStore.clear_expired()
        logger.info("Done!")
        logger.info("Clearing expired UserSessionMap objects ...")
        old_session_maps.delete()
        logger.info(f"Done! Successfully deleted {count} objects")
    else:
        logger.warning("Dry run mode, nothing is cleared or deleted")


class Command(BaseCommand):
    """
    Remove Django session and UserSessionMap objects that have expired when this command is run.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dry",
            action="store_true",
            dest="dry_run",
            help="Run query to find all expired UserSessionMap objects but do not delete them or clear sessions",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        clear_expired_sessions(dry_run=dry_run)
