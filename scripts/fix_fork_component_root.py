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
        nodes = AbstractNode.objects.filter(is_fork=True)

        for node in nodes:
            if not node.root == node.get_root():
                logger.info(
                    'Fixing {} (node): Replacing {} (wrong root) with {} (correct root)'.format(node._id, node.root._id, node.get_root()._id)
                )
                node.root = node.get_root()
                node.save()

        if dry:
            raise Exception('Abort Transaction - Dry Run')
    print('Done')

if __name__ == '__main__':
    main()
