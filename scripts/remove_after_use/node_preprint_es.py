import django
django.setup()
import sys
import logging
from django.db import transaction

from scripts import utils as script_utils
from website.search.elastic_search import delete_doc
from osf.models import Preprint, AbstractNode
logger = logging.getLogger(__name__)

# To run: docker-compose run --rm web python -m scripts.remove_after_use.node_preprint_search_mig
def main(dry=True):
    """
    Temporary script for updating elastic search after the node-preprint divorce
    - Removes nodes from the index that are categorized as preprints
    - Adds these nodes to the index, this time categorized as nodes
    - Adds preprints to the index, categorized as preprints
    """
    with transaction.atomic():
        for p in Preprint.objects.all():
            p.update_search() # create new index for preprint
            delete_doc(p.node._id, p.node, category='preprint') # delete old index for node categorized as a preprint
            p.node.update_search() # create new index for node (this time categorized as a node)
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    # Finally run the migration
    main(dry=dry)
