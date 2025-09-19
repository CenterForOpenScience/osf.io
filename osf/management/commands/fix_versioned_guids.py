import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Prefetch

from osf.models import GuidVersionsThrough, Guid, Preprint
from osf.utils.workflows import ReviewStates

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Run the command without saving changes',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        fix_versioned_guids(dry_run=dry_run)
        if dry_run:
            transaction.set_rollback(True)


def fix_versioned_guids(dry_run: bool):
    content_type = ContentType.objects.get_for_model(Preprint)
    versions_queryset = GuidVersionsThrough.objects.order_by('-version')
    processed_count = 0
    updated_count = 0
    skipped_count = 0
    errors_count = 0
    for guid in (
        Guid.objects.filter(content_type=content_type)
        .prefetch_related(Prefetch('versions', queryset=versions_queryset))
        .iterator(chunk_size=500)
    ):
        processed_count += 1
        if not guid.versions:
            skipped_count += 1
            continue
        for version in guid.versions.all():
            last_version_object_id = version.object_id
            if guid.object_id == last_version_object_id:
                skipped_count += 1
                break
            if version.referent.machine_state == ReviewStates.INITIAL.value:
                continue
            try:
                guid.object_id = last_version_object_id
                guid.referent = version.referent
                if not dry_run:
                    guid.save()
                updated_count += 1
            except Exception as e:
                logger.error(f"Error occurred during patching {guid._id=}", exc_info=e)
                errors_count += 1

    if dry_run:
        logger.error(
            f"Processed: {processed_count}, Would update: {updated_count}, Skipped: {skipped_count}, Errors: {errors_count}"
        )
    else:
        logger.error(
            f"Processed: {processed_count}, Updated: {updated_count}, Skipped: {skipped_count}, Errors: {errors_count}"
        )
