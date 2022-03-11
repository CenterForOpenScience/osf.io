import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from osf.models import Node, NodeLog

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


def fix_quickfiles_waterbutler_logs():
    '''
    '''
    nodes = Node.objects.filter(
        logs__action=NodeLog.MIGRATED_QUICK_FILES
    ).filter(
        logs__action__in=['addon_file_renamed', 'osf_storage_file_added']
    )
    for node in nodes:
        for log in node.logs.filter(action='addon_file_renamed'):
            log.params['params_node'].update({'id': node._id})

            url = swap_guid(log.params['source']['url'], node)
            log.params['source'].update({'url': url})
            log.params['destination'].update({'url': url})
            log.save()

        for log in node.logs.filter(action='osf_storage_file_added'):
            log.params['params_node'].update({'id': node._id})

            url = swap_guid_view_download(log.params['urls']['view'], node)
            log.params['urls'] = {
                'view': url,
                'download': f'{url}?action=download'
            }
            log.save()

        node.save()


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
        with transaction.atomic():
            fix_quickfiles_waterbutler_logs(dry_run=dry_run, batch_size=batch_size)
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back')
