"""
This will add an ultimate_parent field to all nodes.
Ultimate_parent will be the primary key of the originating parent node
"""

import sys
import logging
from modularodm import Q
from website import models
from website.app import init_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    logger.warn('ultimate_parent field will be added to all nodes.')
    if dry_run:
        logger.warn('Dry_run mode')
    all_nodes = models.Node.find()
    all_nodes_count = all_nodes.count()
    touched_counter = 0
    logger.info('There are {} total nodes'.format(all_nodes_count))
    for node in all_nodes:
        if not getattr(node, 'parent', None):
            touched_counter += 1
            children = [child for child in node.get_descendants_recursive(include=lambda n: n.primary)]
            if dry_run:
                logger.info(
                    '{}/{}: touched node {} with children {}'.format(
                        touched_counter,
                        all_nodes_count,
                        node._id,
                        [child._id for child in children]
                    )
                )
            else:
                node.save()
            for child in children:
                touched_counter += 1
                if dry_run:
                    logger.info(
                        '{}/{}: touched node {} with parent {}'.format(
                            touched_counter,
                            all_nodes_count,
                            child._id,
                            child.parent_id
                        )
                    )
                else:
                    child.save()
    assert (all_nodes_count == touched_counter)


if __name__ == '__main__':
    main()
