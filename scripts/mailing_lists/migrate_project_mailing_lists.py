# -*- coding: utf-8 -*-
"""Create mailing lists for all top-level projects
"""
import logging
import sys

from modularodm import Q

from framework.mongo import database
from framework.mongo.utils import paginated
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
    return paginated(Node)

def migrate(dry_run=True):
    if dry_run:
        create_list = fake
    else:
        create_list = real_create_list

    successful_enables = []
    successful_noops = []
    successful_disables = []
    mailgun_failures = []
    unknown_failures = {}
    nodes = get_targets()
    ncount = Node.find().count()
    i = 0
    logger.info('Preparing to migrate {} nodes.'.format(ncount))
    for node in nodes:
        i += 1
        try:
            assert isinstance(node, Node)
        except:
            continue

        if not node.is_mutable_project:
            try:
                node_kind = 'immutable project'
                if node.is_registration:
                    node_kind = 'registration'
                elif node.is_collection:
                    node_kind = 'collection' 
                elif node.is_deleted:
                    node_kind = 'deleted project' 
                logger.info('({done}/{total}) Disabling mailing list for {kind} {_id}'.format(done=i, total=ncount, _id=node._id, kind=node_kind)
                )
                database['node'].find_and_modify(
                    {'_id': node._id},
                    {'$set': {'mailing_enabled': False,
                              'mailing_updated': False}
                    }
                )
                successful_disables.append(node._id)
            except Exception as e:
                logger.exception('Error while handling node {}'.format(node._id))
                unknown_failures[node._id] = e
        else:
            subscription = NotificationSubscription.load(to_subscription_key(node._id, EVENT))
            if subscription:
                assert node.mailing_enabled
                logger.info('({0}/{1}) Mailing list for node {2} already enabled'.format(i, ncount, node._id))
                successful_noops.append(node._id)
                continue
            try:
                subscription = NotificationSubscription(
                    _id=to_subscription_key(node._id, EVENT),
                    owner=node,
                    event_name=EVENT
                )
                logger.info('({0}/{1}) Enabling mailing list for node {2}'.format(i, ncount, node._id))

                for user in node.contributors:
                    if user.is_active:
                        logger.info('Subscribing user {} on node {}'.format(user, node))
                        subscription.add_user_to_subscription(user, SUBSCRIPTION_TYPE)
                        # users added on `create_list`

                subscription.save()
                database['node'].find_and_modify(
                    {'_id': node._id},
                    {'$set': {'mailing_enabled': True}}
                )
                successful_enables.append(node._id)
            except Exception as e:
                logger.exception('Error while handling node {}'.format(node._id))
                unknown_failures[node._id] = e
            else:
                try:
                    create_list(node._id)
                except Exception as e:
                    logger.exception('Mailgun: error while creating list for node {}'.format(node._id))
                    # Sync this node later
                    mailgun_failures.append(node.id)
                    database['node'].find_and_modify(
                        {'_id': node._id},
                        {'$set': {'mailing_updated': True}}
                    )
                else:
                    # Node synced
                    database['node'].find_and_modify(
                        {'_id': node._id},
                        {'$set': {'mailing_updated': False}}
                    )

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

    if successful_noops:
        logger.info(
            "Successfully skipped {0} nodes that were already configured:\n{1}".format(
                len(successful_noops), successful_noops
            )
        )

    if mailgun_failures:
        logger.error('Encountered {0} problems when making API calls to mailgun:\n{1}'.format(
                len(mailgun_failures), mailgun_failures
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
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        migrate(dry_run=dry_run)

if __name__ == '__main__':
    main()
