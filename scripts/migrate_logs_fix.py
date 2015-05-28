import sys
import logging

from website.app import init_app
from website.models import NodeLog
from scripts import utils as script_utils
from modularodm import Q

logger = logging.getLogger(__name__)


def do_migration(records, dry=False):
    for log in records:
        logger.info(
            'Migrating log - {}, '.format(log._id)
        )
        count = 0
        if not dry:
            log.should_hide = False
            for node in log.logged:
                if node != log.node:
                    node.logs.remove(log)
                    count += 1
                    node.save()
                    log.was_connected_to.append(node)

            log.save()

            logger.info(
                'Removed {} nodes from log - {}'.format(
                    count, log._id)
            )

    logger.info('{}Migrated {} logs'.format('[dry]'if dry else '', len(records)))


def get_targets():
    return NodeLog.find(Q('should_hide', 'eq', True))


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    do_migration(get_targets(), dry)


if __name__ == '__main__':
    main()
