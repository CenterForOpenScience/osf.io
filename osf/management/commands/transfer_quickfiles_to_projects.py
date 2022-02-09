import logging

from django.db import connection, transaction, utils
from django.core.management.base import BaseCommand

from osf.models import (
    OSFUser,
    QuickFilesNode,
    NodeLog,
    Node
)
from osf.models.quickfiles import get_quickfiles_project_title

from addons.osfstorage.models import OsfStorageFile
from website import mails, settings

logger = logging.getLogger(__name__)
QUICKFILES_DESC = 'The Quick Files feature was discontinued and it’s files were migrated into this Project on March' \
                  ' 11, 2022. The file URL’s will still resolve properly, and the Quick Files logs are available in' \
                  ' the Project’s Recent Activity.'


def remove_quickfiles(dry_run=False):
    quick_files_ids = QuickFilesNode.objects.values_list('id', flat=True)
    quick_files_node_with_files_ids = OsfStorageFile.objects.filter(
        target_object_id__in=quick_files_ids
    ).values_list(
        'target_object_id',
        flat=True
    )
    quick_files_nodes = QuickFilesNode.objects.filter(id__in=quick_files_node_with_files_ids)

    node_logs = [
        NodeLog(
            node=quick_files_node,
            user=quick_files_node.creator,
            original_node=quick_files_node,
            action=NodeLog.MIGRATED_QUICK_FILES
        ) for quick_files_node in quick_files_nodes
    ]
    if not dry_run:
        NodeLog.objects.bulk_create(node_logs)

    logger.info(f'{quick_files_nodes.count()} quickfiles nodes were projectified.')

    QuickFilesNode.bulk_update_search(quick_files_nodes)

    if not dry_run:
        quick_files_nodes.update(
            type='osf.node',
            description=QUICKFILES_DESC
        )
        result = QuickFilesNode.objects.all().delete()
        logger.info(f'Quickfiles deleted {result}')
        with connection.cursor() as cursor:
            cursor.execute("""DROP INDEX IF EXISTS one_quickfiles_per_user RESTRICT;""")
        logger.info('`one_quickfiles_per_user` constraint dropped.')

    for log in node_logs:
        node = log.node
        if not dry_run:
            mails.send_mail(
                to_addr=node.creator.email,
                mail=mails.QUICKFILES_MIGRATED,
                user=node.creator,
                osf_support_email=settings.OSF_SUPPORT_EMAIL,
                can_change_preferences=False,
                quickfiles_link=node.absolute_url
            )


def reverse_remove_quickfiles(dry_run=False):
    if not dry_run:
        Node.objects.filter(
            logs__action=NodeLog.MIGRATED_QUICK_FILES
        ).update(
            type='osf.quickfilesnode'
        )
        users_without_nodes = OSFUser.objects.exclude(
            id__in=QuickFilesNode.objects.all().values_list(
                'creator__id',
                flat=True
            )
        )
        quickfiles_created = []
        for user in users_without_nodes:
            quickfiles_created.append(
                QuickFilesNode(
                    title=get_quickfiles_project_title(user),
                    creator=user
                )
            )

        QuickFilesNode.objects.bulk_create(quickfiles_created)

    if not dry_run:
        with transaction.atomic():
            for quickfiles in quickfiles_created:
                quickfiles.add_addon('osfstorage', auth=None, log=False)
                quickfiles.save()

    if not dry_run:
        savepoint = transaction.savepoint()
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX one_quickfiles_per_user ON osf_abstractnode (creator_id, type, is_deleted)
                    WHERE type='osf.quickfilesnode' AND is_deleted=FALSE;
                    """
                )
            except (utils.OperationalError, utils.ProgrammingError, utils.IntegrityError):
                transaction.savepoint_rollback(savepoint)
        logger.info('`one_quickfiles_per_user` constraint was reinstated.')

    NodeLog.objects.filter(action=NodeLog.MIGRATED_QUICK_FILES).delete()
    QuickFilesNode.bulk_update_search(QuickFilesNode.objects.all())

    logger.info(f'{len(quickfiles_created)} quickfiles were restored.')


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
            required=False,
        )
        parser.add_argument(
            '--reverse',
            type=bool,
            help='is the reverse to be run?.',
            required=False,
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        reverse = options.get('reverse', False)
        if reverse:
            reverse_remove_quickfiles(dry_run)
        else:
            remove_quickfiles(dry_run)
