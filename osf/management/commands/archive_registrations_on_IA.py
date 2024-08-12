import logging
import django

django.setup()

import time
from framework.celery_tasks import app as celery_app
from osf.models import Registration
from website import settings
from osf.utils.requests import requests_retry_session

logger = logging.getLogger(__name__)
django.setup()

from django.core.management.base import BaseCommand


@celery_app.task(name="osf.management.commands.archive_registrations_on_IA")
def archive_registrations_on_IA(dry_run=False, batch_size=100, guids=None):
    if guids:
        registrations = Registration.objects.filter(guids___id__in=guids)
    else:
        # randomize order so large registrations won't block all pigeon workers,
        # and stuck registrations won't block repeatedly
        registrations = Registration.find_ia_backlog().order_by("?")[
            :batch_size
        ]

    logger.info(f"{registrations.count()} to be archived in batch")

    for registration in registrations:
        time.sleep(0.1)  # Don't DDOS self
        if not dry_run:
            logger.info(f"archiving {registration._id}")
            requests_retry_session().post(
                f"{settings.OSF_PIGEON_URL}archive/{registration._id}"
            )
        else:
            logger.info(f"DRY RUN for archiving {registration._id}")


class Command(BaseCommand):
    """
    Nightly task to take a number of Registrations and gradually archive them on archive.org via our archiving service
    osf-pigeon
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dry",
            action="store_true",
            dest="dry_run",
            help="Run migration and roll back changes to db",
        )
        parser.add_argument(
            "--batch_size",
            "-b",
            type=int,
            help="number of registrations to archive.",
        )
        parser.add_argument(
            "guids",
            type=str,
            nargs="+",
            help="List of guids to archive.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        batch_size = options.get("batch_size", 100)
        guids = options.get("guids", [])
        archive_registrations_on_IA(
            dry_run=dry_run, batch_size=batch_size, guids=guids
        )
