# -*- coding: utf-8 -*-
""" Cron script that attempts to ensure synchronicity between
    remote mailing lists on MailGun and their local representations.
"""
import logging

from modularodm import Q

from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.mailing_list.utils import full_update as real_full_update
from website.project.model import Node

from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def fake(*args, **kwargs):
    # Override actual method to prevent outgoing calls
    return

def main(dry_run=True):
    init_app(routes=False)
    if dry_run:
        full_update = fake
    else:
        full_update = real_full_update

    updated_nodes = Node.find(Q('mailing_updated', 'eq', True))
    for node in updated_nodes:
        # reload the node to ensure that it is current
        node.reload()
        if not node.is_mutable_project:
            assert node.is_deleted
        # Reset mailing_updated now in case of a user-change during this update
        node.mailing_updated = False
        node.save()

        try:
            full_update(node._id)
        except Exception as e:
            logger.exception(
                'Unexpected error raised when updating list of '
                'node {}. Continuing...'.format(node._id))
            node.mailing_updated = True
            node.save()
        else:
            logger.info('Successfully updated node {}'.format(node._id))

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')

@celery_app.task(name='scripts.mailing_lists.update_project_mailing_list')
def run_main(dry_run=True):
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        main(dry_run=dry_run)

if __name__ == '__main__':
    with TokuTransaction():
        main()
