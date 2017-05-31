import sys
import logging
from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction
from website.models import Node
from framework.mongo.utils import paginated

from framework.mongo import database


logger = logging.getLogger(__name__)

def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    count = 0
    for node in paginated(Node, increment=1000):
        if not node.root or node.root._id != node._root._id:
            count += 1
            logger.info('Setting root for node {} to {}'.format(node._id, node._root._id))
            node.root = node._root._id
            if not dry:
                node.save()
    logger.info('Finished migrating {} nodes'.format(count))

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
