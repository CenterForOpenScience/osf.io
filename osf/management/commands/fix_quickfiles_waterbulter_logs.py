import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from osf.models import Node, NodeLog
from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import enqueue_task
from django.db.models import Q


logger = logging.getLogger(__name__)


def swap_guid(url, node):
    url = url.split('/')[:-1]
    url[2] = node._id
    url = '/'.join(url)
    return f'{url}?/pid={node._id}'


def swap_guid_view_download(url, node):
    url = url.split('/')[:-1]
    url[1] = node._id
    url = '/'.join(url)
    url = url.partition('?pid=')[0] + f'/?pid={node._id}'
    return url


error_causing_log_actions = {
    'addon_file_renamed',
    'addon_file_moved',
    'addon_file_copied',
}

dead_links_actions = {
    'osf_storage_file_added',
    'file_tag_removed',
    'file_tag_added',
    'osf_storage_file_removed',
    'osf_storage_file_updated',
}

affected_log_actions = error_causing_log_actions.union(dead_links_actions)


@celery_app.task()
def fix_logs(node_id, dry_run=False):
    '''
    Fixes view/download links for waterbutler based file logs, and also fixes old 10 digit node params for moved/renamed
    files.
    '''
    logger.info(f'{node_id} Quickfiles logs started')

    with transaction.atomic():
        logger.debug(f'{node_id} Quickfiles logs started')

        node = Node.load(node_id)
        for log in node.logs.filter(action__in=error_causing_log_actions):
            log.params['params_node'] = {
                '_id': node._id,
                'title': node.title
            }

            url = swap_guid(log.params['source']['url'], node)
            log.params['destination'].update({'url': url})

            if log.action == 'addon_file_renamed':
                log.params['source'].update({'url': url})

            log.save()

        for log in node.logs.filter(action__in=dead_links_actions):
            log.params['params_node'] = {
                '_id': node._id,
                'title': node.title
            }

            url = swap_guid_view_download(log.params['urls']['view'], node)
            log.params['urls'] = {
                'view': url,
                'download': f'{url}&action=download'
            }
            log.save()

        node.save()
        if dry_run:
            raise RuntimeError('This was a dry run.')

    logger.info(f'{node._id} Quickfiles logs fixed')


def fix_quickfiles_waterbutler_logs(dry_run=False):
    nodes = Node.objects.filter(
        logs__action=NodeLog.MIGRATED_QUICK_FILES
    ).filter(
        logs__action__in=affected_log_actions
    ).distinct('pk')
    logger.info(f'{nodes.count()} Quickfiles nodes with bugged logs found.')

    for node in nodes:
        logger.info(f'{node._id} Quickfiles logs fixing started')
        enqueue_task(fix_logs.s(node._id, dry_run=dry_run))


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        fix_quickfiles_waterbutler_logs(dry_run=dry_run)
