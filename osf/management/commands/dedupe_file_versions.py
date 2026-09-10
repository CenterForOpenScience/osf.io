import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from osf.models.files import BaseFileNode, BaseFileVersionsThrough
from osf.utils.requests import check_select_for_update

logger = logging.getLogger(__name__)


def find_duplicate_groups():
    """
    Yields {'basefilenode_id', 'fileversion__identifier', 'count'} for every
    (file, identifier) pair that has more than one linked FileVersion.
    """
    return (
        BaseFileVersionsThrough.objects
        .values('basefilenode_id', 'fileversion__identifier')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
        .order_by('basefilenode_id')
    )


def fetch_group_rows(basefilenode_id, identifier):
    # `fileversion__id` is a secondary sort key so the choice of keeper is fully
    # deterministic even if two duplicates share the exact same `created` timestamp.
    return list(
        BaseFileVersionsThrough.objects
        .filter(basefilenode_id=basefilenode_id, fileversion__identifier=identifier)
        .select_related('fileversion')
        .order_by('fileversion__created', 'fileversion__id')
    )


def log_group(file_label, identifier, row_to_keep, rows_to_delete, dry_run):
    logger.info(
        f'{"[DRY-RUN] " if dry_run else ""}file={file_label} identifier={identifier} '
        f'keeping {row_to_keep.fileversion._id} (location={row_to_keep.fileversion.location}) '
        f'discarding={[(row.fileversion._id, row.fileversion.location) for row in rows_to_delete]}'
    )


def resolve_group(basefilenode_id, identifier, file_label, dry_run):
    """
    Fetches the current rows for one duplicate group, logs the keep/discard
    decision, unless dry_run - deletes the discarded duplicate(s.
    """
    through_rows = fetch_group_rows(basefilenode_id, identifier)
    if len(through_rows) < 2:
        return False

    row_to_keep, rows_to_delete = through_rows[0], through_rows[1:]
    log_group(file_label, identifier, row_to_keep, rows_to_delete, dry_run=dry_run)

    if not dry_run:
        for row in rows_to_delete:
            row.delete()

    return True


def dedupe_file_versions(dry_run=True):
    """
    Finds FileVersions that share the same `identifier` for the same file because of
    race condition in OsfStorageFile.create_version() and delete duplicate
    """
    if dry_run:
        logger.info('[DRY-RUN] Data will not be modified.')

    groups = list(find_duplicate_groups())
    file_labels = dict(
        BaseFileNode.objects
        .filter(id__in={group['basefilenode_id'] for group in groups})
        .values_list('id', '_id')
    )

    fixed = 0

    for group in groups:
        basefilenode_id = group['basefilenode_id']
        identifier = group['fileversion__identifier']
        file_label = file_labels.get(basefilenode_id, basefilenode_id)

        if dry_run:
            resolved = resolve_group(basefilenode_id, identifier, file_label, dry_run=True)
        else:
            with transaction.atomic():
                if check_select_for_update():
                    # Lock the file row for the duration of this group's cleanup so
                    # a concurrent create_version() call for the same file can't
                    # interleave with the read-then-delete in resolve_group().
                    BaseFileNode.objects.select_for_update().get(pk=basefilenode_id)
                resolved = resolve_group(basefilenode_id, identifier, file_label, dry_run=False)

        if resolved:
            fixed += 1

    logger.info(f'{fixed} duplicate group(s) resolved.')
    return fixed


class Command(BaseCommand):
    help = """
    Finds FileVersions that share the same `identifier` on the same file because of
    a race condition in OsfStorageFile.create_version() and delete duplicate
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_false',
            dest='dry_run',
            default=True,
            help='Actually unlink duplicate versions. Without this flag, only reports what would change.',
        )

    # Management command handler
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', True)
        dedupe_file_versions(dry_run=dry_run)
