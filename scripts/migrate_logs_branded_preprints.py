import sys
import logging

from website.app import init_app
from website.models import NodeLog, PreprintService
from scripts import utils as script_utils
from modularodm import Q

logger = logging.getLogger(__name__)


def do_migration(records, dry=False):
    count = 0

    for log in records:
        provider = PreprintService.find_one(Q('node', 'eq', log.params.get('node'))).provider

        logger.info(
            'Migrating log - {} - to add Provider: {}, '.format(log._id, provider._id)
        )

        if not dry:
            log.params['preprint_provider'] = provider._id
            log.save()

        count += 1

    logger.info('{}Migrated {} logs'.format('[dry]'if dry else '', count))


def get_targets():
    return NodeLog.find(
        Q('action', 'eq', 'preprint_initiated') &
        Q('params.preprint_provider', 'exists', False)
    )


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    do_migration(get_targets(), dry)


if __name__ == '__main__':
    main()
