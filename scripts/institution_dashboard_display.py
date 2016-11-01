import sys
import logging

from modularodm import Q

from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.institutions.model import Institution
from website.project.model import Node
from website.settings import INSTITUTION_DISPLAY_NODE_THRESHOLD


logger = logging.getLogger(__name__)


def set_institution_dashboard_display():
    all_institutions = Institution.find()
    for inst in all_institutions:
        logger.info(
            'Finding affiliated nodes for Institution with id <{}> and title <{}>'.format(inst._id, inst.name)
        )
        affiliated_nodes = Node.find_by_institutions(
            inst,
            query=(
                Q('is_public', 'eq', True) &
                Q('is_folder', 'ne', True) &
                Q('is_deleted', 'ne', True) &
                Q('parent_node', 'eq', None) &
                Q('is_registration', 'eq', False)
            )
        )
        logger.info(
            'Found {} affiliated nodes for Institution with id <{}> and title <{}>'.format(
                len(affiliated_nodes), inst._id, inst.name)
        )

        inst.node.institution_dashboard_display = True if len(affiliated_nodes) >= INSTITUTION_DISPLAY_NODE_THRESHOLD else False
        inst.node.save()


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
