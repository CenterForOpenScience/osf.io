#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate retracted registrations so that their date modified is date of retraction."""

import sys
import logging

from modularodm import Q
from website.models import Node, NodeLog
from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

logger = logging.getLogger(__name__)


def do_migration(logs):
    # ... perform the migration using a list of logs ...
    for log in logs:
        registration_id = log.params.get('registration')
        if registration_id:
            registration = Node.load(registration_id)
            if registration.date_modified < log.date:
                registration.date_modified = log.date
                registration.save()
                logger.info('{} date updated to {}'.format(registration, log.date))
            else:
                logger.info('Date modified is more recent than retraction ' + log._id)
        else:
            logger.warning('No parent registration found for retraction log ' + log._id)


def get_targets():
    # ... return the list of logs whose registrations we want to migrate ...
    targets = NodeLog.find(Q('action', 'eq', 'retraction_approved'))

    logger.info('Retractions found: {}'.format(len(targets)))
    return targets


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)

    with TokuTransaction():
        init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
        targets = get_targets()
        for target in targets:
            logger.info('{} {}: {}'.format(target.date, target.params.get('registration'), target.action))
        do_migration(targets)
        if dry:
            raise RuntimeError('Dry run, rolling back transaction.')
