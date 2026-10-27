import logging

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef

from osf.models import OSFUser

logger = logging.getLogger(__name__)

COLLECTION_READ_WRITE_GROUP_REGEX = r'^collections_\d+_(read|write)$'


def _has_members():
    return Exists(OSFUser.groups.through.objects.filter(group_id=OuterRef('id')))


def remove_collection_read_write_groups(dry_run=False, batch_size=10000):
    """Delete the collections_<id>_read and collections_<id>_write groups.

    Collections only create an admin group now, and nothing ever added users to the
    read/write groups. A group that does have members is skipped and logged.
    Returns (deleted, skipped_with_members).
    """
    groups = Group.objects.filter(name__regex=COLLECTION_READ_WRITE_GROUP_REGEX)

    with_members = list(
        groups.filter(_has_members()).values_list('name', flat=True)
    )
    for name in with_members:
        logger.warning(f'Skipping {name}: it has members')

    if dry_run:
        to_delete = groups.exclude(_has_members()).count()
        logger.info(f'[DRY RUN] Would delete {to_delete} collection read/write groups')
        return to_delete, len(with_members)

    deleted = 0
    last_id = 0
    while True:
        batch_ids = list(
            groups.filter(id__gt=last_id).order_by('id').values_list('id', flat=True)[:batch_size]
        )
        if not batch_ids:
            break
        last_id = batch_ids[-1]
        with transaction.atomic():
            # Emptiness is re-checked here so a group that gained a member since the
            # batch was selected is left alone
            _, per_model = Group.objects.filter(id__in=batch_ids).exclude(_has_members()).delete()
        batch_deleted = per_model.get('auth.Group', 0)
        deleted += batch_deleted
        logger.info(f'Deleted {batch_deleted} groups (total {deleted}, last id {last_id})')

    logger.info(f'Deleted {deleted} collection read/write groups, skipped {len(with_members)} with members')
    return deleted, len(with_members)


class Command(BaseCommand):
    help = (
        'Delete the empty collections_<id>_read and collections_<id>_write auth groups, '
        'and their object permissions. Collections no longer create these groups. '
        'Groups with members are skipped.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            action='store_true',
            default=False,
            help='Count the groups that would be deleted without deleting them',
        )
        parser.add_argument(
            '--batch_size',
            type=int,
            default=10000,
            help='How many groups to delete per transaction',
        )

    def handle(self, *args, **options):
        remove_collection_read_write_groups(
            dry_run=options['dry_run'],
            batch_size=options['batch_size'],
        )
