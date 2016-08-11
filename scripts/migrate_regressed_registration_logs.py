"""
Some registration-related logs have regressed where there is 1) no params['registration'] field, 2) params['node'] field points to registration,
and original node field is incorrect(since original_node = params['node'].

This is causing some logs to link to registrations instead of nodes.
"""

import logging
import sys
from modularodm import Q

from framework.transactions.context import TokuTransaction

from website.models import Node, NodeLog, RegistrationApproval
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    targets = get_targets()
    fix_log_params(targets)
    reg_approved_logs = get_registration_approved_logs()
    fix_reg_approved_log_params(reg_approved_logs)


def get_targets():
    """
    These logs are potentially missing params['registration'] fields.  Params['node'] and original_node fields may incorrectly
    be pointing to the registration instead of the node.
    """
    logs = NodeLog.find(
        Q('action', 'eq', 'registration_cancelled') |
        Q('action', 'eq', 'retraction_approved') |
        Q('action', 'eq', 'retraction_cancelled') |
        Q('action', 'eq', 'embargo_approved') |
        Q('action', 'eq', 'embargo_cancelled') |
        Q('action', 'eq', 'embargo_terminated')
    )
    return logs


def get_registration_approved_logs():
    # These logs do not have params['registration'] field
    logs = NodeLog.find(Q('action', 'eq', 'registration_approved') & Q('params.registration', 'eq', None))
    return logs


def fix_log_params(targets):
    """
    Restores params['registration'] field and points params['node'] and original_node fields to the node instead of registration
    """
    logger.info('Migrating registration_cancelled, registration_approved, retraction_cancelled, embargo_approved, embargo_cancelled, and embargo_terminated logs.')
    count = 0
    for log in targets:
        node_id = log.params['node']
        node = Node.load(node_id)
        if node.is_registration:
            log.params['node'] = get_registered_from(node)
            log.params['registration'] = node._id
            log.original_node = log.params['node']
            logger.info('Updating params of log {}. params[node]={}, params[registration]={}, and original_node = {}'.format(log._id, log.params['node'], log.params['registration'], log.original_node))
            log.save()
            count += 1
    logger.info('{} logs migrated'.format(count))


def fix_reg_approved_log_params(targets):
    """
    Restores params['registration'] field
    """
    logger.info('Migrating registration_approved logs.')
    count = 0
    for log in targets:
        log.params['registration'] = RegistrationApproval.load(log.params['registration_approval_id'])._get_registration()._id
        logger.info(
            'Updating params[registration] of log {}. params[node]={}, params[registration]={}'.format(
                log._id, log.params['node'], log.params['registration'], log.original_node))
        log.save()
        count += 1
    logger.info('{} logs migrated'.format(count))


def get_registered_from(registration):
    """
    Gets node registration was registered from.  Handles deleted registrations where registered_from is null.

    """
    if registration.registered_from:
        return registration.registered_from_id
    else:
        log = registration.logs[0] # We assume this is the project created log.
        return log.params.get('node') or log.params.get('project')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')
