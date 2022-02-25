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
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from tqdm import tqdm


logger = logging.getLogger(__name__)
QUICKFILES_DESC = 'The Quick Files feature was discontinued and it’s files were migrated into this Project on March' \
                  ' 11, 2022. The file URL’s will still resolve properly, and the Quick Files logs are available in' \
                  ' the Project’s Recent Activity.'


def paginated_progressbar(queryset, function, page_size=100, dry_run=False):
    paginator = Paginator(queryset, page_size)

    i = 0
    with tqdm(total=len(queryset)) as pbar:
        for page_num in paginator.page_range:
            for item in paginator.page(page_num).object_list:
                if not dry_run:
                    function(item)
                pbar.update(1)


def remove_quickfiles(dry_run=False, page_size=1000):
    quick_files_ids = QuickFilesNode.objects.values_list('id', flat=True)
    quick_files_node_with_files_ids = OsfStorageFile.objects.filter(
        target_object_id__in=quick_files_ids,
        target_content_type=ContentType.objects.get_for_model(QuickFilesNode)
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
        logger.info(f'{len(node_logs)} node logs were added.')

    if not dry_run:
        quick_files_count = quick_files_nodes.count()
        quick_files_nodes.update(
            type='osf.node',
            description=QUICKFILES_DESC
        )
        logger.info(f'{quick_files_count} quickfiles nodes were projectified.')

        paginated_progressbar(
            QuickFilesNode.objects.all(),
            lambda item: item.delete(),
            page_size=page_size,
            dry_run=dry_run
        )
        logger.info(f'All Quickfiles deleted')

    if not dry_run:
        paginated_progressbar(
            node_logs,
            lambda log: mails.send_mail(
                to_addr=log.node.creator.email,
                mail=mails.QUICKFILES_MIGRATED,
                user=log.node.creator,
                osf_support_email=settings.OSF_SUPPORT_EMAIL,
                can_change_preferences=False,
                quickfiles_link=log.node.absolute_url
            ),
            page_size=page_size,
            dry_run=dry_run,
        )
        logger.info('quickfiles removal emails sent')


def reverse_remove_quickfiles(dry_run=False, page_size=1000):
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

    NodeLog.objects.filter(action=NodeLog.MIGRATED_QUICK_FILES).delete()

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
        parser.add_argument(
            '--page',
            type=int,
            help='how many many query items should be in a page?',
            required=False,
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        reverse = options.get('reverse', False)
        page_size = options.get('page', 1000)
        if reverse:
            reverse_remove_quickfiles(dry_run)
        else:
            remove_quickfiles(dry_run)
