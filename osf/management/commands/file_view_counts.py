from __future__ import unicode_literals
import logging

import django
django.setup()
import json
import requests
import urllib


from django.core.management.base import BaseCommand
from django.db import transaction
from osf.models import BaseFileNode, PageCounter
from website import settings
from keen import KeenClient

from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def set_file_view_counts(state, *args, **kwargs):
    # get all osfstorage files which is_deleted == False
    files = BaseFileNode.resolve_class('osfstorage', BaseFileNode.FILE).active.all()

    for file_node in files:
        # for each file get the file view counts from keen
        client = KeenClient(
            project_id=settings.KEEN['public']['project_id'],
            read_key=settings.KEEN['public']['read_key'],
        )

        node_pageviews = client.count(
            event_collection='pageviews',
            timeframe='this_7_days',
            group_by='node.id',
            filters=[
                {
                    'property_name': 'node.id',
                    'operator': 'exists',
                    'property_value': True
                }
            ]
        )

        query = [{'property_name': 'page.info.path', 'operator': 'eq', 'property_value': file_node._id}]

        query = urllib.quote(json.dumps(query))
        url = 'https://api.keen.io/3.0/projects/{}/queries/count' \
              '?api_key={}&event_collection=pageviews&timezone=UTC&timeframe' \
              '=this_14_days&filters={}'.format(settings.KEEN['public']['project_id'], settings.KEEN['public']['read_key'], query)
        resp = requests.get(url)
        file_view_count = int(resp.json()['result'])

        # udpate the pagecounter for file view counts
        PageCounter.set_basic_counters('view:{0}:{1}'.format(file_node.node._id, file_node._id), file_view_count)

        logger.info('File ID {0}: has inputed "{1}" view counts'.format(file_node._id, file_view_count))

    logger.info('File view counts migration from keen completed.')


class Command(BaseCommand):
    """
    Backfill Retraction.date_retracted with `RETRACTION_APPROVED` log date.
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            set_file_view_counts
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back.')
