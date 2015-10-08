#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to migrate Box credentials from user settings object to external
account objects.

Changes:
 - Create external account for authorized user settings
 - Attach external account to user settings
 - Attach external account to all node settings
"""

import sys
import logging
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction
from framework.mongo import database

from website.addons.box.model import BoxUserSettings
from website.addons.box.model import BoxNodeSettings
from website.oauth.models import ExternalAccount

logger = logging.getLogger(__name__)


def do_migration(records):
    database['boxnodesettings'].update({'user_settings': {'$type': 2}}, {'$rename': { 'user_settings': 'foreign_user_settings'}}, multi=True)

    for user_addon in records:
        user = user_addon.owner
        old_account = user_addon.oauth_settings

        logger.info('Record found for user {}'.format(user._id))

        # Create/load external account and append to user
        try:
            account = ExternalAccount(
                provider='box',
                provider_name='Box',
                display_name=old_account.username,
                oauth_key=old_account.access_token,
                refresh_token=old_account.refresh_token,
                provider_id=old_account.user_id,
                expires_at=old_account.expires_at,
            )
            account.save()
        except KeyExistsException:
            # ... or get the old one
            account = ExternalAccount.find_one(
                Q('provider', 'eq', 'box') &
                Q('provider_id', 'eq', old_account.user_id)
            )
            assert account is not None
        user.external_accounts.append(account)
        user.save()

        # Remove oauth_settings from user settings object
        user_addon.oauth_settings = None
        user_addon.save()

        logger.info('Added external account {0} to user {1}'.format(
            account._id, user._id,
        ))

    for node in BoxNodeSettings.find():
        if node.foreign_user_settings is None:
            continue
        logger.info('Migrating user_settings for box {}'.format(node._id))
        node.user_settings = node.foreign_user_settings
        node.save()


def get_targets():
    return BoxUserSettings.find(
        Q('oauth_settings', 'ne', None)
    )


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    with TokuTransaction():
        do_migration(get_targets())
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
