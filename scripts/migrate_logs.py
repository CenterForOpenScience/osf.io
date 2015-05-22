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
            'Migrating logs in node - {}, '.format(node._id)
        )
        count = 0
        for log in node.logs:
            if not dry:
                if log and node != log.resolve_node(node):
                    log.should_hide = True
                    log.save()
                    count += 1

                    logger.info(
                        'Migrating log - {} in node - {}, log action is {}'.format(
                            log._id, node._id, log.action
                        )
                    )

        logger.info(
            '{}Migrated {} logs in node - {}'.format(
                '[dry]'if dry else '', count, node._id)
        )

        total += count

    logger.info('{}Migrated {} logs'.format('[dry]'if dry else '', total))


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
