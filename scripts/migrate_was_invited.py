#!/usr/bin/env python
# encoding: utf-8

import sys
import logging

from modularodm import Q

from website import models
from website.app import init_app
from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def is_invited(user):
    query = (
        Q('action', 'eq', 'contributor_added') &
        Q('params.contributors', 'eq', user._id)
    )
    if user.date_confirmed:
        query = (
            query &
            Q('date', 'ne', None) &
            Q('date', 'lt', user.date_confirmed)
        )
    logs = models.NodeLog.find(query)
    return bool(logs)


def main(dry_run=True):
    users = models.User.find(Q('is_invited', 'eq', None))
    for user in users:
        invited = is_invited(user)
        logger.info('Setting `is_invited` field of user {0} to {1}'.format(user._id, invited))
        if not dry_run:
            user.is_invited = invited
            user.save()


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(set_backends=True, routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)
