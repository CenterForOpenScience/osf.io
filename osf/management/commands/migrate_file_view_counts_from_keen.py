from __future__ import unicode_literals
import logging

import django
django.setup()
import json
import requests
import urllib

from addons.osfstorage.models import OsfStorageFile
from django.core.management.base import BaseCommand
from django.db import transaction
from osf.models import PageCounter
from website import settings

from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def set_file_view_counts(state, *args, **kwargs):
    # get all osfstorage files which is_deleted == False, the file size in production database > 1730325
    files = OsfStorageFile.objects.all()

    # the limit of the datasets size return from keen is 400kb.
    # A json file return 3 file counts from keen is about 223 bytes
    # So a json file return from keen should be able to reach 4800 files, to be safe use 4500
    keen_file_limit = 4500

    while files:
        file_array = files[:keen_file_limit]
        file_ids = [x._id for x in file_array]
        # for each file get the file view counts from keen
        query = [{'property_name': 'page.info.path', 'operator': 'in', 'property_value': file_ids}]
        query = urllib.quote(json.dumps(query))

        url = 'https://api.keen.io/3.0/projects/{}/queries/count' \
              '?api_key={}&event_collection=pageviews&timezone=UTC&timeframe' \
              '=this_14_days&filters={}&group_by={}'.format(settings.KEEN['private']['project_id'],
                                                            settings.KEEN['private']['read_key'], query, 'file._id')
        resp = requests.get(url)
        files_view_counts = resp.json()['result']

        for data in files_view_counts:
            file_id = data['file._id']
            count = data['result']

            file_node = OsfStorageFile.load(file_id)

            # udpate the pagecounter for file view counts
            PageCounter.set_basic_counters('view:{0}:{1}'.format(file_node.node._id, file_node._id), count)

            logger.info('File ID {0}: has inputed "{1}" view counts'.format(file_node._id, count))

        files = files[keen_file_limit:]

    logger.info('File view counts migration from keen completed.')


class Command(BaseCommand):
    """
    Migrate initiate pagecounter  file view counts from keen
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
            set_file_view_counts()
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back.')
