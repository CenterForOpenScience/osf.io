# -*- coding: utf-8 -*-
"""Before today (the day that this script was created), embargoed components were not being made public at their
parent registration's embargo end date. This script will find affected components and make them public.
"""
import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website import models
from website.app import init_app
from scripts import utils as scripts_utils
logger = logging.getLogger(__name__)

def main(dry_run):
    n_affected = 0
    completed_embargoes = models.Embargo.find(Q('state', 'eq', models.Embargo.COMPLETED))
    for embargo in completed_embargoes:
        parent_registration = models.Node.find_one(Q('embargo', 'eq', embargo))
        if len(parent_registration.nodes):
            if any((each.is_public is False for each in parent_registration.nodes)):
                n_affected += 1
                logger.info('GUID: {}'.format(parent_registration._id))
                logger.info('Contributors: {}'.format(', '.join([each.fullname for each in parent_registration.contributors])))
                for child in parent_registration.nodes:
                    if not child.is_public:
                        logger.info('Making child node {} public'.format(child._id))
                        if not dry_run:
                            with TokuTransaction():
                                child.set_privacy('public', auth=None, save=True)
    logger.info('{} affected registrations'.format(n_affected))


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)
