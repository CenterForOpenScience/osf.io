import logging

from modularodm import Q

from website.models import Node
from website.app import init_app


logger = logging.getLogger(__name__)


if __name__ == '__main__':
    """This script will set the analytics read keys for all public nodes. Requires a valid
    keen master key in settings.KEEN['public']['master_key']. Generated keys are stable
    between runs for the same master key.
    """

    init_app(routes=False)

    public_nodes = Node.find(
        Q('is_public', 'eq', True) & Q('is_deleted', 'eq', False)
    )
    total = len(public_nodes)
    logger.info('Adding keen.io read keys to {} public nodes'.format(total))
    count = 0
    for public_node in public_nodes:
        count +=1
        if not count % 10:
            logger.info(' Updating node {} of {}.'.format(count, total))
        public_node.keenio_read_key = public_node.generate_keenio_read_key()
        public_node.save()

    logger.info('Done! {} nodes updated.'.format(count))

    logger.info('Verifying...')
    nodes_with_keen_keys = Node.find(
        Q('is_public', 'eq', True) & Q('is_deleted', 'eq', False)
        & Q('keenio_read_key', 'ne', '') & Q('keenio_read_key', 'ne', None)
    )
    total_with_keys = len(nodes_with_keen_keys)
    logger.info('Found {} nodes with keenio keys, expected {}'.format(total_with_keys, count))
    if total_with_keys != total:
        logger.error('...AND THAT IS UNACCEPTABLE!')
    else:
        logger.info('...well done, all.')
