#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import logging
from modularodm import Q

from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

from addons.dataverse.model import AddonDataverseNodeSettings

logger = logging.getLogger(__name__)


def do_migration():
    for node_addon in AddonDataverseNodeSettings.find(Q('foreign_user_settings', 'ne', None)):
        user_addon = node_addon.foreign_user_settings
        if not user_addon.external_accounts:
            logger.warning('User {0} has no dataverse external account'.format(user_addon.owner._id))
            continue
        account = user_addon.external_accounts[0]
        node_addon.set_auth(account, user_addon.owner)
        logger.info('Added external account {0} to node {1}'.format(
            account._id, node_addon.owner._id,
        ))


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    with TokuTransaction():
        do_migration()
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
