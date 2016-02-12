# -*- coding: utf-8 -*-
"""Create mailing lists for all top-level projects
"""
import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.models import Node
from website.project import mailing_list as mails
from website import settings
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def get_targets():
    return list(Node.find(Q('is_dashboard', 'eq', False)))

def migrate(dry_run=True):
    successful_creates = []
    failed_deletes = {}
    unknown_failures = {}
    nodes = get_targets()
    ncount = len(nodes)
    logger.info('Preparing to migrate {} nodes.'.format(ncount))
    for node in nodes:
        for user in node.contributors:
            if not user.is_active:
                logger.info('Unsubscribing user {} on node {} since it is not active'.format(user, node))
                node.mailing_unsubs.append(user)

        try:        
            logger.info('({0}/{1})Creating mailing list for node {2}'.format(nodes.index(node), ncount, node._id))
            node.mailing_enabled = True
            mails.create_list(title=node.title, **node.mailing_params)
            node.save()
            successful_creates.append(node._id)
            if dry_run:
                try:
                    mails.delete_list(node_id=node._id)
                except HTTPError as e:
                    failed_deletes[node._id] = e
        except Exception as e:
            unknown_failures[node._id] = e

    logger.info(
        "Created {0} new mailing lists for nodes:\n{1}".format(
            len(successful_creates), successful_creates
        )
    )

    if failed_deletes:
        logger.error('Failed to delete {0} lists during (dry) run:\n{1}\n\nPlease delete them manually through Mailgun\n'.format(
                len(failed_deletes), ['({}, {})'.format(nid, failed_deletes[nid]) for nid in failed_deletes.keys()]
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
    migrate(dry_run=dry_run)

if __name__ == '__main__':
    main()
