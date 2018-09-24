import logging
import sys
import argparse
import datetime

import django
django.setup()

from elasticsearch2.helpers import bulk
from elasticsearch_dsl.connections import connections

from osf.models import PageCounter, PreprintService
from scripts import utils
from website.search.elastic_search import client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():

    es = connections.get_connection()

    dry = '--dry' in sys.argv
    preprints = PreprintService.objects.all().values_list('node__guids___id', 'node__preprint_file___id', 'guids___id',
                                              'provider___id')

    batch_to_update = []
    for preprint in preprints:
        node__id, file_id, preprint__id, provider__id = preprint
        page_counters = PageCounter.objects.filter(_id__startswith='download:{node__id}:{file_id}:'.format(node__id=node__id,
                                                                                                      file_id=file_id)).values_list('_id', 'date')
        for page_counter in page_counters:
            page_counter__id, date = page_counter
            version_num = page_counter__id.split(':')[-1]
            for date, totals in date.items():
                for _ in range(0, totals['total']):
                    batch_to_update.append({
                        '_index': 'osf_preprintdownload-{}'.format(date.replace('/', '.')),
                        '_source': {
                            'path': '/{}'.format(file_id),
                            'preprint_id': preprint__id,
                            'provider_id': provider__id,
                            'timestamp': datetime.datetime.strptime(date, '%Y/%m/%d'),
                            'user_id': None,  # Pagecounter never tracked this
                            'version': int(version_num) + 1
                        },
                        '_type': 'doc'
                    })

    logger.info('This will migrate {} Pagecounter entries to Elasticsearch'.format(len(batch_to_update)))
    if not dry:
        utils.add_file_logger(logger, __file__)
        bulk(es, batch_to_update)


if __name__ == '__main__':
    main()

