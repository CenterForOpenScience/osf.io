"""Script to backfill PageCounter data into elasticsearch.

* This MUST be run before enabling the elasticsearch_metrics switch.
* This MUST run to completion without errors. If an error occurs, delete
  the existing osf_preprint* indices, fix the error, and re-run the script.
"""
import logging
import sys
import argparse
import datetime
import progressbar
from time import sleep

from website.app import setup_django
setup_django()

from elasticsearch.helpers import bulk
from elasticsearch_dsl.connections import connections

from osf.models import PageCounter, PreprintService
from scripts import utils
from website.search.elastic_search import client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CHUNK_SIZE = 100
MAX_BATCH_SIZE = 1000
THROTTLE_PERIOD = 3  # seconds
REQUEST_TIMEOUT = 30  # seconds


def main():

    es = connections.get_connection()

    dry = '--dry' in sys.argv
    if not dry:
        utils.add_file_logger(logger, __file__)
    preprints = PreprintService.objects.all().values_list('node__guids___id', 'node__preprint_file___id', 'guids___id',
                                              'provider___id')

    logger.info('Collecting data on {} preprints...'.format(preprints.count()))

    progress_bar = progressbar.ProgressBar(maxval=preprints.count()).start()
    batch_to_update = []
    for i, preprint in enumerate(preprints, 1):
        progress_bar.update(i)
        node__id, file_id, preprint__id, provider__id = preprint
        page_counters = PageCounter.objects.filter(_id__startswith='download:{node__id}:{file_id}:'.format(node__id=node__id,
                                                                                                      file_id=file_id)).values_list('_id', 'date')
        for page_counter in page_counters:
            page_counter__id, date = page_counter
            version_num = page_counter__id.split(':')[-1]
            for date, totals in date.items():
                batch_to_update.append({
                    '_index': 'osf_preprintdownload-{}'.format(date.replace('/', '.')),
                    '_source': {
                        'count': totals['total'],
                        'path': '/{}'.format(file_id),
                        'preprint_id': preprint__id,
                        'provider_id': provider__id,
                        'timestamp': datetime.datetime.strptime(date, '%Y/%m/%d'),
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
                    sleep(THROTTLE_PERIOD)

    # Index final batch
    if len(batch_to_update):
        logger.info('Bulk-indexing data from {} PageCounter records'.format(len(batch_to_update)))
        if not dry:
            bulk(es, batch_to_update, max_retries=3, chunk_size=CHUNK_SIZE, request_timeout=REQUEST_TIMEOUT)

    progress_bar.finish()
    logger.info('This will migrate {} Pagecounter entries to Elasticsearch'.format(len(batch_to_update)))


if __name__ == '__main__':
    main()

