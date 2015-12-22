"""
This will add a root and parent_node fields to all nodes.
Root will be the primary key of the originating parent node.
Parent_node will be the first primary parent
Done so that you can filter on both root nodes and parent nodes with a DB query
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


def do_migration(dry=True):
    all_nodes = models.Node.find(
        Q('is_deleted', 'eq', False) &
        (Q('root', 'eq', None) | Q('root', 'exists', False))
    )
    all_nodes_count = all_nodes.count()
    touched_counter = 0
    errored_nodes = []
    logger.info('Migrating {} nodes'.format(all_nodes_count))
    for node in all_nodes:
        with TokuTransaction():
            if not getattr(node, '_parent_node', None):
                touched_counter += 1
                logger.info('Attempting to save node {}'.format(node._id))
                if not dry:
                    try:
                        node.save()
                    except (KeyError, RuntimeError) as err:  # Workaround for nodes whose files were unmigrated in a previous migration
                        logger.error('Error occurred when trying to save node: {}'.format(node._id))
                        logger.exception(err)
                        errored_nodes.append(node)
                children = [child for child in node.get_descendants_recursive(include=lambda n: n.primary and not n.is_deleted)]
                logger.info(
                    '{}/{}: touched node {} with children {}'.format(
                        touched_counter,
                        all_nodes_count,
                        node._id,
                        [child._id for child in children]
                    )
                )

                assert node.root._id == node._id
                assert not getattr(node, 'parent_node', None)
                logger.info('Parent Node Saving: Saved Node {} with root {}'.format(node._id, node.root))

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

                    if not dry:
                        try:
                            child.save()
                        except (KeyError, RuntimeError) as err:  # Workaround for nodes whose files were unmigrated in a previous migration
                            logger.error('Error occurred when trying to save child: {}'.format(node._id))
                            logger.exception(err)
                            errored_nodes.append(child)
                    logger.info('\tChild Node saved: Verifying that save Node {} with root {}'.format(child._id, child.root))
                    # Need this check due to an inconsistency in prod data where
                    # a node's parent is deleted by the node itself is not deleted
                    if child.parent_node:
                        assert child.parent_node._id == child.parent_id
                        assert child.root._id == node._id
                    else:
                        logger.error('Child {} has a null parent node')
                        logger.error('This may be because its parent was deleted without the child being deleted')

    if errored_nodes:
        logger.error('{} errored nodes:'.format(len(errored_nodes)))
        logger.error('\n'.join([each._id for each in errored_nodes]))
    else:
        logger.info('Finished with no errors.')


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    do_migration(dry=dry)


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)

