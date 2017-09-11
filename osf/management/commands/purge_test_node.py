from __future__ import unicode_literals
import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import Node
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def remove_logs_and_files(node_guid):
    assert node_guid, 'Expected truthy node_id, got {}'.format(node_guid)
    n = Node.load(node_guid)
    assert n, 'Unable to find node with guid {}'.format(node_guid)
    logger.info('Deleting file versions...')
    for file in n.files.exclude(parent__isnull=True):
        file.versions.all().delete()
    logger.info('Deleting file nodes...')
    n.files.exclude(parent__isnull=True).delete()
    logger.info('Deleting logs...')
    n.logs.exclude(id=n.logs.earliest().id).delete()

class Command(BaseCommand):
    """
    Removes all logs and non-root files from a node.
    For cleaning up after RunScope tests that get out of hand.
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--node',
            type=str,
            action='store',
            dest='node_id',
            required=True,
            help='Node guid to purge data from',
        )
        parser.add_argument(
            '--i-am-really-sure-about-this',
            action='store_true',
            dest='really_delete',
            help='Actually delete data'
        )

    def handle(self, *args, **options):
        really_delete = options.get('really_delete', False)
        node_id = options.get('node_id', None)
        if really_delete:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            remove_logs_and_files(node_id)
            if not really_delete:
                raise RuntimeError('Not certain enough -- transaction rolled back')
