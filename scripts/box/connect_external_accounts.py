#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
First run 
    rm -rf website/addons/box/views/
to remove old .pyc files that would interfere.
"""
import sys
import logging
from modularodm import Q

from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

from website.addons.box.model import BoxNodeSettings

logger = logging.getLogger(__name__)


def do_migration():
    for node_addon in BoxNodeSettings.find(Q('foreign_user_settings', 'ne', None)):
        user_addon = node_addon.foreign_user_settings
        user = user_addon.owner
        if not user_addon.external_accounts:
            logger.warning('User {0} has no box external account'.format(user._id))
            continue
        account = user_addon.external_accounts[0]
        node_addon.set_auth(account, user_addon.owner)

        user_addon.grant_oauth_access(
            node=node_addon.owner,
            external_account=account,
            metadata={'folder': node_addon.folder_id}
        )

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
