"""Remove None from nodes' logs lists."""
import sys
import logging

from website.app import init_app
from website.models import Node
from scripts import utils as script_utils
from modularodm import Q

logger = logging.getLogger(__name__)


def do_migration(records, dry=False):
    count = 0
    for node in records:
        # Can't use in operator to check if None in node.logs
        # Due to modm bug: https://github.com/CenterForOpenScience/modular-odm/issues/110
        # So instead, we build an intermediate list
        if None in [each for each in node.logs]:
            logger.info(
                'Removing None logs in node {}'.format(node._id)
            )
            node.logs = [each for each in node.logs if each is not None]
            node.save()
            count += 1
    logger.info('Removed None logs from {} nodes'.format(count))


def get_targets():
    return Node.find(Q('is_deleted', 'ne', True))


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    do_migration(get_targets(), dry)


if __name__ == '__main__':
    main()
