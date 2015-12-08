"""
This will add an ultimate_parent field to all nodes.
Ultimate_parent will be the primary key of the originating parent node
"""

import sys
import logging
from modularodm import Q
from website import models
from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def do_migration():
    init_app(routes=False)
    logger.warn('ultimate_parent field will be added to all nodes.')
    all_nodes = models.Node.find()
    all_nodes_count = all_nodes.count()
    touched_counter = 0
    logger.info('There are {} total nodes'.format(all_nodes_count))
    for node in all_nodes:
        if not getattr(node, 'parent_node', None):
            touched_counter += 1
            node.save()
            children = [child for child in node.get_descendants_recursive(include=lambda n: n.primary)]
            logger.info(
                '{}/{}: touched node {} with children {}'.format(
                    touched_counter,
                    all_nodes_count,
                    node._id,
                    [child._id for child in children]
                )
            )

            assert node.ultimate_parent == node._id
            logger.info('Saved Node {} with ultimate_parent {}'.format(node._id, node.ultimate_parent))

            for child in children:
                touched_counter += 1
                logger.info(
                    '{}/{}: touched node {} with parent {}'.format(
                        touched_counter,
                        all_nodes_count,
                        child._id,
                        child.parent_id
                    )
                )

                child.save()
                assert child.ultimate_parent == node.ultimate_parent
                logger.info('Saved Node {} with ultimate_parent {}'.format(child._id, child.ultimate_parent))

    assert all_nodes_count == touched_counter


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    with TokuTransaction():
        do_migration()
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)

