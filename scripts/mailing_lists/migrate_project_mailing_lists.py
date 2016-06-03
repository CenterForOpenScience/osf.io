# -*- coding: utf-8 -*-
"""Create mailing lists for all top-level projects
"""
import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.mailing_list.utils import create_list as real_create_list
from website.models import Node
from website.notifications.model import NotificationSubscription
from website.notifications.utils import to_subscription_key
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

EVENT = 'mailing_list_events'
SUBSCRIPTION_TYPE = 'email_transactional'

def fake(*args, **kwargs):
    # Override actual method to prevent outgoing calls
    return

def get_targets():
    return Node.find()

def migrate(dry_run=True):
    if dry_run:
        create_list = fake
    else:
        create_list = real_create_list

    successful_enables = []
    successful_disables = []
    unknown_failures = {}
    nodes = get_targets()
    ncount = len(nodes)
    logger.info('Preparing to migrate {} nodes.'.format(ncount))
    for i, node in enumerate(nodes):
        if not node.is_mutable_project:
            try:
                logger.info('({0}/{1})Disabling mailing list for registration/dashboard {2}'.format(i+1, ncount, node._id))
                node.mailing_enabled = False    
                node.mailing_updated = False
                node.save()
                successful_disables.append(node._id)
            except Exception as e:
                logger.exception('Error while handling node {}'.format(node._id))
                unknown_failures[node._id] = e
        else:
            try:
                subscription = NotificationSubscription(
                    _id=to_subscription_key(node._id, EVENT),
                    owner=node,
                    event_name=EVENT
                )
                logger.info('({0}/{1})Enabling mailing list for node {2}'.format(i+1, ncount, node._id))
                node.mailing_enabled = True
                node.mailing_updated = True

                for user in node.contributors:
                    if user.is_active:
                        logger.info('Subscribing user {} on node {}'.format(user, node))
                        subscription.add_user_to_subscription(user, SUBSCRIPTION_TYPE)
                        # users added on `create_list`

                subscription.save()
                node.save()
                successful_enables.append(node._id)
            except Exception as e:
                logger.exception('Error while handling node {}'.format(node._id))
                unknown_failures[node._id] = e
            else:
                create_list(node._id)
        if i % 100 == 0:
            for key in ('node', 'user', 'fileversion', 'storedfilenode'):
                Node._cache.data.get(key, {}).clear()
                Node._object_cache.data.get(key, {}).clear()


    logger.info(
        "Successfully enabled {0} new mailing lists for nodes:\n{1}".format(
            len(successful_enables), successful_enables
        )
    )

    logger.info(
        "Successfully disabled {0} new mailing lists for registrations/dashboards:\n{1}".format(
            len(successful_disables), successful_disables
        )
    )

    if unknown_failures:
        logger.error('Handled {0} unknown exceptions while creating lists:\n{1}'.format(
                len(unknown_failures), ['({}, {})'.format(nid, unknown_failures[nid]) for nid in unknown_failures.keys()]
            )
        )

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')


def main():
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        migrate(dry_run=dry_run)

if __name__ == '__main__':
    main()
