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
    AbstractNode,
    Guid
)

from osf.models.base import generate_guid
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
QUICKFILES_DATE = datetime.datetime(2022, 3, 11, tzinfo=pytz.utc)


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
        ).order_by('pk')

        Guid.objects.filter(
            id__in=quick_files_nodes.values_list('guids__id', flat=True)
        ).delete()

        # generate unique guids prior to record creation to avoid collisions.
        guids = set([])
        while len(guids) < quick_files_node_with_files_ids.count():
            guids.add(generate_guid())
        guids = list(guids)

        guids = [
            Guid(
                _id=_id,
                object_id=node,
                content_type=ContentType.objects.get_for_model(Node)
            ) for _id, node in zip(guids, quick_files_node_with_files_ids)
        ]
        Guid.objects.bulk_create(guids)

        node_logs = [
            NodeLog(
                node=node,
                user=node.creator,
                original_node=node,
                params={'node': node._id},
                action=NodeLog.MIGRATED_QUICK_FILES
            ) for node in quick_files_nodes
        ]
        NodeLog.objects.bulk_create(node_logs)

        queued_mail = [
            QueuedMail(
                user=node.creator,
                to_addr=node.creator.email,
                send_at=QUICKFILES_DATE,
                email_type=mails.QUICKFILES_MIGRATED.tpl_prefix,
                data=dict(
                    osf_support_email=settings.OSF_SUPPORT_EMAIL,
                    can_change_preferences=False,
                    quickfiles_link=node.absolute_url
                )
            ) for node in quick_files_nodes
        ]
        QueuedMail.objects.bulk_create(queued_mail)

        for i, node in enumerate(quick_files_nodes):
            # update guid in logs
            for log in node.logs.all():
                log.params['node'] = node._id
                log.save()

            if i and not i % page_size:
                logger.info(f'{i} quickfiles were projectified at {datetime.datetime.now()}')

        quick_files_nodes.update(description=QUICKFILES_DESC, type='osf.node')

        logger.info(f'all quickfiles with files were projectified.')


def reverse_remove_quickfiles(dry_run=False, page_size=1000):
    with transaction.atomic():
        quickfiles_nodes_with_files = AbstractNode.objects.filter(
            logs__action=NodeLog.MIGRATED_QUICK_FILES
        )
        quickfiles_nodes_with_files.update(
            type='osf.quickfilesnode',
            is_deleted=False,
            deleted=None,
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

        logger.info(f'{len(QuickFilesNode.objects.all())} quickfiles were restored.')


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
