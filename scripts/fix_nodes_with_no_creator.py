import logging
import sys

from django.db import transaction

from website.app import setup_django
setup_django()
from osf.models import AbstractNode
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def main():
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        qs = AbstractNode.objects.filter(creator__isnull=True)
        logger.info(f'Found {qs.count()} nodes with no creator')
        for node in AbstractNode.objects.filter(creator__isnull=True):
            logger.info(f'Setting the creator for AbstractNode {node._id} to the first contrbutor')
            AbstractNode.objects.filter(id=node.id).update(creator=node.contributors.first())
        if dry:
            raise Exception('Abort Transaction - Dry Run')
    print('Done')

if __name__ == '__main__':
    main()
