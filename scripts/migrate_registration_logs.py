"""
This migration will change params['node'] to be the node (if it isn't node already), and will set
params['registration'] equal to the associated registration.
"""

import logging

from modularodm import Q

from website.models import NodeLog, Node, RegistrationApproval
from website.app import init_app

from scripts import utils as script_utils
from framework.mongo import database as db
from framework.transactions.context import TokuTransaction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_targets():
    """
    Fetches all registration-related logs except for project_registered.

    project_registered log is not included because params already correct.
    """
    logs = NodeLog.find(
        Q('action', 'eq', 'registration_initiated') |
        Q('action', 'eq', 'registration_approved') |
        Q('action', 'eq', 'registration_cancelled') |  # On staging, there are a few inconsistencies with these.  Majority of params['node'] are registrations, but a handful are nodes.
        Q('action', 'eq', 'retraction_initiated') |
        Q('action', 'eq', 'retraction_approved') |  # params['node'] is already equal to node.  Adds registration_field below.  Will be slow.
        Q('action', 'eq', 'retraction_cancelled') |
        Q('action', 'eq', 'embargo_initiated') |
        Q('action', 'eq', 'embargo_approved') |
        Q('action', 'eq', 'embargo_completed') |
        Q('action', 'eq', 'embargo_cancelled')
    )
    return logs


def get_registered_from(registration):
    """
    Gets node registration was registered from.  Handles deleted registrations where registered_from is null.

    """
    if registration.registered_from:
        return registration.registered_from_id
    else:
        first_log = db['node'].find_one({'_id': registration._id})['logs'][0]
        return NodeLog.load(first_log).params['node']


def migrate_log(logs):
    """
    Migrates registration logs to set params['node'] to registered_from and params['registration'] to the registration.
    """
    logs_count = logs.count()
    count = 0
    for log in logs:
        count += 1
        params_node = Node.load(log.params['node'])
        if params_node.is_registration:
            log.params['node'] = get_registered_from(params_node)
            log.params['registration'] = params_node._id
        else:
            # For logs where params['node'] already equal to node (registration_approval logs, and logs with errors in registration_cancelled)
            log.params['registration'] = RegistrationApproval.load(log.params['registration_approval_id'])._get_registration()._id

        log.save()
        logger.info('{}/{} Finished migrating log {}: registration action {}. params[node]={} and params[registration]={}'.format(count,
            logs_count, log._id, log.action, log.params['node'], log.params['registration']))


def main(dry_run):
    logs = get_targets()
    migrate_log(logs)
    if not dry_run:
        logger.info('Finished migrate {} logs '.format(len(logs)))
    else:
        raise RuntimeError('Dry Run -- Transaction rolled back')


if __name__ == '__main__':
    import sys
    script_utils.add_file_logger(logger, __file__)
    dry_run = '--dry' in sys.argv
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        main(dry_run=dry_run)
