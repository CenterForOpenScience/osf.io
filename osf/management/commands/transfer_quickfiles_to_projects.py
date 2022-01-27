import logging

from django.db import connection
from django.core.management.base import BaseCommand

from osf.models import (
    OSFUser,
    QuickFilesNode,
    NodeLog
)

from addons.osfstorage.models import OsfStorageFile

logger = logging.getLogger(__name__)


def remove_quickfiles(dry_run=False):
    quick_files_ids = QuickFilesNode.objects.values_list('id', flat=True)
    quick_files_node_with_files_ids = OsfStorageFile.objects.filter(
        target_object_id__in=quick_files_ids
    ).values_list(
        'target_object_id',
        flat=True
    )
    quick_files_nodes = QuickFilesNode.objects.filter(id__in=quick_files_node_with_files_ids)

    for quick_file_node in quick_files_nodes:
        if not dry_run:
            NodeLog.objects.create(
                node=quick_file_node,
                action=NodeLog.MIGRATED_QUICK_FILES
            )

    logger.info(f'{quick_files_nodes.count()} nodes projectified.')
    if not dry_run:
        quick_files_nodes.update(type='osf.node')
        result = QuickFilesNode.objects.all().delete()
        logger.debug(f'Quickfiles deleted {result}')
        with connection.cursor() as cursor:
            cursor.execute("""DROP INDEX IF EXISTS one_quickfiles_per_user RESTRICT;""")
        logger.debug('`one_quickfiles_per_user` constraint dropped.')


def reverse_remove_quickfiles(dry_run=False):
    users = OSFUser.objects.all()
    for user in users:
        type_swapped_qf = user.nodes.filter(logs__action=NodeLog.MIGRATED_QUICK_FILES)
        if type_swapped_qf:
            if not dry_run:
                type_swapped_qf.update(type='osf.quickfilesnode')
        else:
            if not dry_run:
                QuickFilesNode.objects.create_for_user(user)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE UNIQUE INDEX one_quickfiles_per_user ON osf_abstractnode (creator_id, type, is_deleted)
                WHERE type='osf.quickfilesnode' AND is_deleted=FALSE;
                """
            )
        logger.debug('`one_quickfiles_per_user` constraint was reinstated.')

    logger.info(f'{users.count()} quickfiles were restored.')

class Command(BaseCommand):
    """
    Puts all Quickfiles into projects or reverses the effect.
    """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )
        parser.add_argument(
            'reverse',
            type=bool,
            help='is the reverse to be run?.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', None)
        reverse = options.get('reverse', None)
        if reverse:
            reverse_remove_quickfiles(dry_run)
        else:
            remove_quickfiles(dry_run)
