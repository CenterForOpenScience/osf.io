#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate retracted registrations so that their date modified is date of retraction."""

import sys
import logging

from modularodm import Q
from website.models import Node, NodeLog

from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def do_migration(logs):
    # ... perform the migration using a list of logs ...
    for log in logs:
        when = log.date
        registration = Node.load(log.params['registration'])

        registration.update_fields(date_modified=when)
        registration.save()

        logger.warning("{} date updated to {}".format(registration, when))


def get_targets():
    # ... return the list of logs whose registrations we want to migrate ...
    query = Q('action', 'eq', "retraction_approved")
    targets = NodeLog.find(query)

    logger.info("Retractions found: {}".format(len(targets)))
    return targets


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models

    targets = get_targets()

    if dry:
        for target in targets:
            logger.info("{} {}: {}".format(target.date, target.params['registration'], target.action))
    else:
        do_migration(targets)

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
