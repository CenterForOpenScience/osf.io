import pytz
import logging
import datetime

from django.db import transaction
from django.db.models import Exists, F, Func, OuterRef, Value
from django.core.management.base import BaseCommand
from tqdm import tqdm

from osf.models import (
    OSFUser,
    QuickFilesNode,
    NodeLog,
    AbstractNode,
    Guid,
)
from osf.models.base import generate_guid
from osf.models.quickfiles import get_quickfiles_project_title
from osf.models.queued_mail import QueuedMail
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField

from addons.osfstorage.models import OsfStorageFile
from website import mails, settings
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)
QUICKFILES_DESC = 'The Quick Files feature was discontinued and it’s files were migrated into this Project on March' \
                  ' 11, 2022. The file URL’s will still resolve properly, and the Quick Files logs are available in' \
                  ' the Project’s Recent Activity.'
QUICKFILES_DATE = datetime.datetime(2022, 3, 11, tzinfo=pytz.utc)


def remove_quickfiles():
    node_content_type = ContentType.objects.get_for_model(AbstractNode)
    quick_file_annotation = Exists(
        OsfStorageFile.objects.filter(
            target_object_id=OuterRef('id'),
            target_content_type=node_content_type
        )
    )
    quick_files_nodes = QuickFilesNode.objects.annotate(has_files=quick_file_annotation).filter(has_files=True)
    target_count = quick_files_nodes.count()
    logger.info(f'Acquired {target_count} targets')

    _ = Guid.objects.filter(
        id__in=quick_files_nodes.values_list('guids__id', flat=True)
    ).delete()
    logger.info(f'Deleted guids: {_}')

    # generate unique guids prior to record creation to avoid collisions, set object ensures all guids are unique
    guids = set()
    while len(guids) < target_count:
        guids.add(generate_guid())
    guids = list(guids)
    logger.info(f'Generated {len(guids)} Guids')

    guids = [
        Guid(
            _id=_id,
            object_id=node_id,
            content_type=node_content_type,
        ) for _id, node_id in zip(guids, quick_files_nodes.values_list('id', flat=True))
    ]
    Guid.objects.bulk_create(guids)
    logger.info(f'Created {len(guids)} Guids')

    node_logs = []
    queued_mail = []
    pbar = tqdm(total=target_count)
    for node in quick_files_nodes:
        node_logs.append(NodeLog(
            node=node,
            user=node.creator,
            original_node=node,
            params={'node': node._id},
            action=NodeLog.MIGRATED_QUICK_FILES
        ))
        queued_mail.append(QueuedMail(
            user=node.creator,
            to_addr=node.creator.email,
            send_at=QUICKFILES_DATE,
            email_type=mails.QUICKFILES_MIGRATED.tpl_prefix,
            data=dict(
                osf_support_email=settings.OSF_SUPPORT_EMAIL,
                can_change_preferences=False,
                quickfiles_link=node.absolute_url
            )
        ))
        node.logs.update(
            params=Func(
                F('params'),
                Value(['node']),
                Value(node._id, DateTimeAwareJSONField()),
                function='jsonb_set'
            )
        )
        pbar.update(1)
    pbar.close()

    logger.info('Updated logs')
    NodeLog.objects.bulk_create(node_logs)
    logger.info(f'Created {len(node_logs)} logs')
    QueuedMail.objects.bulk_create(queued_mail)
    logger.info(f'Created {len(queued_mail)} mails')

    quick_files_nodes.update(description=QUICKFILES_DESC, type='osf.node')
    logger.info(f'Projectified {target_count} QuickFilesNodes')


def reverse_remove_quickfiles():
    quickfiles_nodes_with_files = AbstractNode.objects.filter(
        logs__action=NodeLog.MIGRATED_QUICK_FILES
    )
    for node in quickfiles_nodes_with_files:
        node.guids.all().delete()
        node.save()

    quickfiles_nodes_with_files.update(
        type='osf.quickfilesnode',
        is_deleted=False,
        deleted=None,
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

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        reverse = options.get('reverse', False)
        with transaction.atomic():
            if reverse:
                reverse_remove_quickfiles()
            else:
                remove_quickfiles()
            if dry_run:
                raise RuntimeError('Dry run complete, rolling back.')
