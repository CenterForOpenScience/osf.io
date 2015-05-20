import sys
import logging

from website.app import init_app
from website.models import Node
from scripts import utils as script_utils
from modularodm import Q

logger = logging.getLogger(__name__)


def do_migration(records, dry=False):
    total = 0
    for node in records:
        logger.info(
            'Removing None logs in node - {}, '.format(node._id)
        )
        count = 0
        while None in node.logs:
            node.logs.remove(None)
            count += 1

        if count > 0:
            node.save()

            logger.info(
                '{}Rmoved {} None logs in node - {}'.format(
                    '[dry]'if dry else '', count, node._id)
            )

        total += count

    logger.info('{}Removed {} None logs'.format('[dry]'if dry else '', total))


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