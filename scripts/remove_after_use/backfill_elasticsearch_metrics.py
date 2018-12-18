"""Script to backfill PageCounter data into elasticsearch.

* This MUST be run before enabling the elasticsearch_metrics switch.
* This MUST run to completion without errors. If an error occurs, delete
  the existing osf_preprint* indices, fix the error, and re-run the script.
"""
from __future__ import division
import logging
import sys
import argparse
import datetime
from time import sleep
import pytz

from website.app import setup_django
setup_django()

from django.conf import settings
from elasticsearch.helpers import bulk
from elasticsearch_dsl.connections import connections

from osf.models import PageCounter, Preprint
from scripts import utils
from website.search.elastic_search import client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CHUNK_SIZE = 5000
MAX_BATCH_SIZE = 25000
THROTTLE_PERIOD = 1  # seconds
REQUEST_TIMEOUT = 30  # seconds


def main():

    es = connections.get_connection()

    dry = '--dry' in sys.argv
    if not dry:
        utils.add_file_logger(logger, __file__)
    preprints = Preprint.objects.filter(primary_file__isnull=False).select_related('primary_file', 'provider')
    total_preprints = preprints.count()
    logger.info('Collecting data on {} preprints...'.format(total_preprints))

    batch_to_update = []
    for i, preprint in enumerate(preprints, 1):
        preprint_id = preprint._id
        provider_id = preprint.provider._id
        file_id = preprint.primary_file._id
        page_counters = (
            PageCounter.objects
            .filter(
                _id__startswith='download:{preprint_id}:{file_id}:'.format(
                    preprint_id=preprint_id,
                    file_id=file_id
                )
            ).values_list('_id', 'date')
        )
        for page_counter in page_counters:
            page_counter__id, date = page_counter
            version_num = page_counter__id.split(':')[-1]
            for date, totals in date.items():
                timestamp = datetime.datetime.strptime(date, '%Y/%m/%d').replace(tzinfo=pytz.utc)
                batch_to_update.append({
                    '_index': 'osf_preprintdownload_{}'.format(timestamp.strftime(settings.ELASTICSEARCH_METRICS_DATE_FORMAT)),
                    '_source': {
                        'count': totals['total'],
                        'path': '/{}'.format(file_id),
                        'preprint_id': preprint_id,
                        'provider_id': provider_id,
                        'timestamp': timestamp,
                        'user_id': None,  # Pagecounter never tracked this
                        'version': int(version_num) + 1
                    },
                    '_type': 'doc'
                })

                if len(batch_to_update) >= MAX_BATCH_SIZE:
                    logger.info('Bulk-indexing data from {} PageCounter records'.format(len(batch_to_update)))
                    if not dry:
                        bulk(es, batch_to_update, max_retries=3, chunk_size=CHUNK_SIZE, request_timeout=REQUEST_TIMEOUT)
                    batch_to_update = []
                    # Allow elasticsearch to catch up
                    print('{}/{} preprints completed ({:.2f}%)'.format(i + 1, total_preprints, (i + 1) / total_preprints * 100))
                    sleep(THROTTLE_PERIOD)

    # Index final batch
    if len(batch_to_update):
        logger.info('Bulk-indexing data from {} PageCounter records'.format(len(batch_to_update)))
        if not dry:
            bulk(es, batch_to_update, max_retries=3, chunk_size=CHUNK_SIZE, request_timeout=REQUEST_TIMEOUT)

    logger.info('This will migrate {} Pagecounter entries to Elasticsearch'.format(len(batch_to_update)))


if __name__ == '__main__':
    main()

