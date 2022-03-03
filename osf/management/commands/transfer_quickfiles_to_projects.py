import pytz
import math
import logging
import datetime

from django.db import transaction
from django.core.management.base import BaseCommand

from osf.models import (
    OSFUser,
    QuickFilesNode,
    NodeLog,
    Node,
    AbstractNode
)
from osf.models.quickfiles import get_quickfiles_project_title
from osf.models.queued_mail import QueuedMail

from addons.osfstorage.models import OsfStorageFile
from website import mails, settings
from django.contrib.contenttypes.models import ContentType
from tqdm import tqdm


logger = logging.getLogger(__name__)
QUICKFILES_DESC = 'The Quick Files feature was discontinued and it’s files were migrated into this Project on March' \
                  ' 11, 2022. The file URL’s will still resolve properly, and the Quick Files logs are available in' \
                  ' the Project’s Recent Activity.'


def send_emails(page):
    for log in page:
        new_mail = QueuedMail(
            user=log.node.creator,
            to_addr=log.node.creator.email,
            send_at=datetime.datetime(2022, 3, 11, tzinfo=pytz.utc),
            email_type=mails.QUICKFILES_MIGRATED.tpl_prefix,
            data=dict(
                osf_support_email=settings.OSF_SUPPORT_EMAIL,
                can_change_preferences=False,
                quickfiles_link=log.node.absolute_url
            )
        )
        new_mail.save()


def turn_quickfiles_into_projects(page):
    for node in page:
        node.type = 'osf.node'
        node.description = QUICKFILES_DESC
        node.recast(Node._typedmodels_type)
        node.guids.all().delete()  # remove legacy guid
        node.get_guid(create=True).save()

        # update guid in logs
        for log in node.logs.all():
            log.params['node'] = node._id
            log.save()
        node.save()


def paginated_progressbar(queryset, function, page_size=100, dry_run=False):
    '''
    This is a little strange because Paginator's Page class has a __getitem__ method that list-ifies querysets, this
    function preserved the Django Queryset class allowing calls to the Django object managers, otherwise we'd use
    Django's paginator.
    '''
    with tqdm(total=len(queryset)) as pbar:
        page_range = range(0, math.ceil(len(queryset) / page_size))
        for page_num in page_range:
            if not dry_run:
                if page_num == page_range.stop - 1:
                    function(queryset[page_num * page_size:])
                    pbar.update(len(queryset[page_num * page_size:]))
                else:
                    function(queryset[page_num * page_size: page_num * page_size + page_size])
                    pbar.update(page_size)


def remove_quickfiles(dry_run=False, page_size=1000):
    with transaction.atomic():
        quick_files_ids = QuickFilesNode.objects.values_list('id', flat=True)
        quick_files_node_with_files_ids = OsfStorageFile.objects.filter(
            target_object_id__in=quick_files_ids,
            target_content_type=ContentType.objects.get_for_model(QuickFilesNode)
        ).values_list(
            'target_object_id',
            flat=True
        )
        quick_files_nodes = AbstractNode.objects.filter(
            id__in=quick_files_node_with_files_ids,
            creator__is_active=True,
        ).order_by('pk')

        paginated_progressbar(
            quick_files_nodes,
            lambda page: turn_quickfiles_into_projects(page),
            page_size=page_size,
            dry_run=dry_run
        )
        logger.info(f'all quickfiles with files were projectified.')

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
            paginated_progressbar(
                node_logs,
                lambda page: send_emails(page),
                page_size=page_size,
                dry_run=dry_run,
            )
            logger.info('quickfiles removal emails were queued to be sent at 2022, 3, 11')


def reverse_remove_quickfiles(dry_run=False, page_size=1000):
    with transaction.atomic():
        quickfiles_nodes_with_files = AbstractNode.objects.filter(
            logs__action=NodeLog.MIGRATED_QUICK_FILES
        )
        quickfiles_nodes_with_files.update(
            type='osf.quickfilesnode'
        )

        for node in quickfiles_nodes_with_files:
            node.guids.all().delete()
            node.save()

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

        if not dry_run:
            QuickFilesNode.objects.bulk_create(quickfiles_created)

        if not dry_run:
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
            reverse_remove_quickfiles(dry_run, page_size)
        else:
            remove_quickfiles(dry_run, page_size)
