import sys
import logging
from website.app import setup_django
setup_django()
from scripts import utils as script_utils
from osf.models import AbstractNode
from framework.database import paginated

logger = logging.getLogger(__name__)

def main(dry=True):
    count = 0
    for node in paginated(AbstractNode, increment=1000):
        true_root = node.get_root()
        if not node.root or node.root.id != true_root.id:
            count += 1
            logger.info('Setting root for node {} to {}'.format(node._id, true_root._id))
            if not dry:
                AbstractNode.objects.filter(id=node.id).update(root=true_root)
    logger.info('Finished migrating {} nodes'.format(count))

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
