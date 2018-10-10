import sys
import logging

from website.app import setup_django
setup_django()

from scripts import utils as script_utils
from website.search.elastic_search import client, NOT_ANALYZED_PROPERTY, ENGLISH_ANALYZER_PROPERTY
from website.search_migration.migrate import migrate_collected_metadata
from website.settings import ELASTIC_INDEX as INDEX

logger = logging.getLogger(__name__)

def main(dry=True):
    doc_type = 'collectionSubmission'
    mapping = {
        'properties': {
            'issue': NOT_ANALYZED_PROPERTY,
            'volume': NOT_ANALYZED_PROPERTY,
            'programArea': NOT_ANALYZED_PROPERTY,
        }
    }
    res = client().indices.put_mapping(index=INDEX, doc_type=doc_type, body=mapping, ignore=[400, 404])
    logger.info('{}'.format(res))
    migrate_collected_metadata(INDEX, True)


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
