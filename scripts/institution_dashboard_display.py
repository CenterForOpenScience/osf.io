import sys
import logging

from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.institutions.model import Institution
from website.project import tasks


logger = logging.getLogger(__name__)


def set_institution_dashboard_display():
    for inst in Institution.find():
        tasks.institution_set_dashboard_display(inst)
        logger.info('Dashboard display updated for Institution with id <{}> and name <{}>'.format(inst._id, inst.name))


def main(dry=True):
    init_app(set_backends=True, routes=False)

    with TokuTransaction():
        set_institution_dashboard_display()
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)

    if 'debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif 'warning' in sys.argv:
        logger.setLevel(logging.WARNING)
    elif 'info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif 'error' in sys.argv:
        logger.setLevel(logging.ERROR)

    main(dry=dry)
