# -*- coding: utf-8 -*-

import logging

from modularodm import Q

from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.mailing_list.utils import full_update
from website.project.model import Node

logger = logging.getLogger(__name__)

def main(dry_run=True):
    if dry_run:
        def full_update(*args, **kwargs):
            # Override actual method to prevent outgoing calls
            return

    init_app(routes=False)
    updated_nodes = Node.find(Q('mailing_updated', 'eq', True))
    for node in updated_nodes:
        update_node(node)

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')

def update_node(node):
    # reload the node to ensure that it is current
    node.reload()

    assert not node.is_registration and not node.is_collection

    # Reset mailing_updated now in case of a user-change during this update
    node.mailing_updated = False
    node.save()

    try:
        full_update(node._id)
    except Exception as e:
        logger.error(
            'Unexpected error raised when updating list of '
            'node {}. Continuing...'.format(node._id))
        logger.error(e)
        node.mailing_updated = True
        node.save()
    else:
        logger.info('Successfully updated node {}'.format(node._id))

@celery_app.task(name='scripts.update_project_mailing_list')
def run_main(dry_run=True):
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        main(dry_run=dry_run)

if __name__ == '__main__':
    with TokuTransaction():
        main()
