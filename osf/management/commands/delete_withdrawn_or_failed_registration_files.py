import logging

from framework.celery_tasks import app as celery_app
from osf.models import Registration
from django.core.management.base import BaseCommand
from osf.utils.workflows import RegistrationModerationStates
from website.settings import STUCK_FILES_DELETE_TIMEOUT
from django.db.models import Count
from website.app import setup_django

setup_django()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def mark_withdrawn_files_as_deleted(batch_size, dry_run=False):
    withdrawn_registrations = Registration.objects.filter(
        moderation_state=RegistrationModerationStates.WITHDRAWN.db_name
    )
    logger.info(
        f'{"[DRY-RUN]" if dry_run else ""} There are {withdrawn_registrations.count()} registrations that are stuck'
    )

    for node in withdrawn_registrations.annotate(fc=Count("files")).filter(
        fc__gte=1
    )[:batch_size]:
        files_to_be_deleted = node.files.all()
        logger.info(
            f'{"[DRY-RUN]" if dry_run else ""} There are {files_to_be_deleted.count()} files deleted from withrawn node ({node._id})'
        )
        for file in files_to_be_deleted:
            if not dry_run:
                file.delete()


def mark_failed_registration_files_as_deleted(batch_size, dry_run=False):
    """
    These registrations have ArchiveJobs stuck in initial state after the archive timeout period.
    """
    failed_registrations = Registration.find_failed_registrations(
        days_stuck=STUCK_FILES_DELETE_TIMEOUT
    )
    logger.info(
        f'{"[DRY-RUN]" if dry_run else ""} There are {failed_registrations.count()} registrations that are stuck having there files marked as deleted'
    )

    for reg in failed_registrations.annotate(fc=Count("files")).filter(
        fc__gte=1
    )[:batch_size]:
        reg.delete_registration_tree(save=True)
        files_to_be_deleted = reg.files.all()
        logger.info(
            f'{"[DRY-RUN]" if dry_run else ""} There are {files_to_be_deleted.count()} files deleted from stuck registration ({reg._id})'
        )
        for file in files_to_be_deleted:
            if not dry_run:
                file.delete()


@celery_app.task(
    name="management.commands.delete_withdrawn_or_failed_registration_files"
)
def main(batch_size_withdrawn, batch_size_stuck, dry_run=False):
    """
    This script purges files that are deleted after being withdrawn 30 days.
    """
    if dry_run:
        logger.info(
            "This is a dry run; no files will be purged or marked as deleted."
        )

    # Withdrawn files
    mark_withdrawn_files_as_deleted(dry_run, batch_size_withdrawn)

    # Failed Registration files
    mark_failed_registration_files_as_deleted(dry_run, batch_size_stuck)


class Command(BaseCommand):
    help = """
        This script purges files that are deleted after being withdrawn 30 days.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dry",
            action="store_true",
            dest="dry_run",
            help="Dry run",
        )
        parser.add_argument(
            "--withdrawn",
            type=int,
            dest="batch_size_withdrawn",
        )
        parser.add_argument(
            "--stuck",
            type=int,
            dest="batch_size_withdrawn",
        )

    # Management command handler
    def handle(self, *args, **options):
        dry_run = options.get("dry_run", True)
        batch_size_withdrawn = options.get("batch_size_withdrawn")
        batch_size_stuck = options.get("batch_size_stuck")
        main(
            dry_run=dry_run,
            batch_size_withdrawn=batch_size_withdrawn,
            batch_size_stuck=batch_size_stuck,
        )
