import sys
import logging

from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.addons.osfstorage import model

logger = logging.getLogger(__name__)

def do_migration():
    count = 0
    errored = 0
    for node_settings in model.OsfStorageNodeSettings.find():
        root = model.OsfStorageFileNode.load(node_settings.to_storage()['root_node'])
        for child in iter_children(root):
            if child.node_settings != node_settings:
                logger.info('Update node_settings for {!r} in project {!r}'.format(child, node_settings.owner))
                child.node_settings = node_settings
                try:
                    child.save()
                except Exception as err:
                    errored += 1
                    logger.error('Error occurred while updating {!r}'.format(child))
                    logger.exception(err)
                    logger.error('Skipping...')
                else:
                    count += 1
    logger.info('Updated: {} file nodes'.format(count))
    logger.info('Errored: {} file nodes'.format(errored))


def iter_children(file_node):
    to_go = [file_node]
    while to_go:
        for child in to_go.pop(0).children:
            if child.is_collection:
                to_go.append(child)
            yield child


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
