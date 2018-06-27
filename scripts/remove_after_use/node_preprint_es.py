import django
django.setup()
import sys
import logging
from django.db import transaction

from scripts import utils as script_utils
from website.search.elastic_search import delete_doc
from osf.models import Preprint, AbstractNode
logger = logging.getLogger(__name__)

# To run: docker-compose run --rm web python -m scripts.remove_after_use.node_preprint_es
def main(dry=True):
    """
    Temporary script for updating elastic search after the node-preprint divorce
    - Removes nodes from the index that are categorized as preprints
    - Adds these nodes to the index, this time categorized as nodes
    - Adds preprints to the index, categorized as preprints
    """
    for p in Preprint.objects.all():
        logger.info('Adding preprint {} to index.'.format(p._id))
        if not dry:
            p.update_search() # create new index for preprint
        if p.node:
            logger.info('Deleting node {} from index, with category preprint'.format(p.node._id))
            if not dry:
                delete_doc(p.node._id, p.node, category='preprint') # delete old index for node categorized as a preprint
            logger.info('Creating new index for node {}, with category node.'.format(p.node._id))
            if not dry:
                p.node.update_search() # create new index for node (this time categorized as a node)
    if dry:
        raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    # Finally run the migration
    main(dry=dry)
