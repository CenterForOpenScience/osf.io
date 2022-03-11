import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from osf.models import Node, NodeLog
from framework.celery_tasks import app as celery_app

logger = logging.getLogger(__name__)


def swap_guid(url, node):
    url = url.split('/')
    url[2] = node._id
    url = '/'.join(url)
    return url


def swap_guid_view_download(url, node):
    url = url.split('/')
    url[0] = node._id
    url.pop(1)
    url = '/'.join(url)
    url = url[: url.find('?pid=')] + f'?pid={node._id}'
    return f'/{url}'


@celery_app.task(name='osf.management.commands.fix_quickfiles_waterbutler_logs')
def fix_quickfiles_waterbutler_logs(batch_size=100, dry_run=False):
    '''
    Fixes view/download links for waterbutler based file logs, and also fixes old 10 digit node params for moved/renamed
    files.
    '''
    with transaction.atomic():
        nodes = Node.objects.filter(
            logs__action=NodeLog.MIGRATED_QUICK_FILES
        ).filter(
            logs__action__in=['addon_file_renamed', 'addon_file_moved', 'addon_file_copied', 'osf_storage_file_added', 'file_tag_removed', 'file_tag_added', 'osf_storage_file_removed']
        )[:batch_size]
        i = 0
        for i, node in enumerate(nodes):

            for log in node.logs.filter(action__in=['addon_file_renamed', 'addon_file_moved', 'addon_file_copied']):
                log.params['params_node'].update({'id': node._id})
                url = swap_guid(log.params['source']['url'], node)
                log.params['destination'].update({'url': url})

                if log.action == 'addon_file_renamed':
                    log.params['source'].update({'url': url})

                log.save()

            for log in node.logs.filter(action__in=['osf_storage_file_added', 'file_tag_removed', 'file_tag_added', 'osf_storage_file_removed']):
                log.params['params_node'].update({'id': node._id})
                url = swap_guid_view_download(log.params['urls']['view'], node)
                log.params['urls'] = {
                    'view': url,
                    'download': f'{url}?action=download'
                }
                log.save()

            node.save()

        logger.info(f'{i} Quickfiles logs fixed')

        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back')


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

        parser.add_argument(
            '--batch_size',
            type=int,
            default=0
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        batch_size = options.get('batch_size')
        fix_quickfiles_waterbutler_logs(dry_run=dry_run, batch_size=batch_size)
