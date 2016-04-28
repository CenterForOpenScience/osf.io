"""
Update existing "embargo_approved_no_user" logs to link to registered project instead
of the registration.
"""
import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction

from website.models import Node, NodeLog
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    targets = get_targets()
    fix_embargo_approved_logs(targets)


def get_targets():
    return NodeLog.find(Q('action', 'eq', NodeLog.EMBARGO_APPROVED) & Q('params.user', 'eq', None))


def fix_embargo_approved_logs(targets):
    for log in targets:
        node_id = log.params['node']
        node = Node.load(node_id)
        if node.is_registration:
            log.params['node'] = node.registered_from_id
            log.params['registration'] = node._id
            log.save()
            logging.debug('Updated node param of log {}'.format(log._id))


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')
