import sys
import logging

from website.app import setup_django
setup_django()

from scripts import utils as script_utils
from website.search.elastic_search import client, NOT_ANALYZED_PROPERTY, ENGLISH_ANALYZER_PROPERTY
from website.settings import ELASTIC_INDEX as INDEX

logger = logging.getLogger(__name__)

def main(dry=True):
    doc_type = 'collectionSubmission'
    mapping = {
        'properties': {
            'collectedType': NOT_ANALYZED_PROPERTY,
            'subjects': NOT_ANALYZED_PROPERTY,
            'status': NOT_ANALYZED_PROPERTY,
            'provider': NOT_ANALYZED_PROPERTY,
            'abstract': ENGLISH_ANALYZER_PROPERTY
        }
    }
    res = client().indices.put_mapping(index=INDEX, doc_type=doc_type, body=mapping, ignore=[400, 404])
    logger.info('{}'.format(res))

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
