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

from website.addons.box.model import BoxUserSettings
from website.addons.box.model import BoxNodeSettings
from website.oauth.models import ExternalAccount

logger = logging.getLogger(__name__)


def do_migration(records, dry):
    for user_addon in records:
        user = user_addon.owner
        old_account = user_addon.oauth_settings

        logger.info('Record found for user {}'.format(user._id))

        if not dry:
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
            user_addon.clear()
            user_addon.save()

            logger.info('Added external account {0} to user {1}'.format(
                account._id, user._id,
            ))

        if dry:
            logger.info('[Dry] Creating Box ExternalAccount:\n\tdisplay_name={0}\n\toauth_key={1}\n\trefresh_token={2}\n\tprovider_id={3}'.format(
                old_account.username, old_account.access_token, old_account.refresh_token, old_account.user_id
            ))
            logger.info('[Dry] Added external account to user {0}'.format(
                user._id,
            ))

            for node_addon in get_authorized_node_settings(user_addon):
                logger.info('[Dry] Added external account to node {0}'.format(
                    node_addon.owner._id,
                ))



def get_targets():
    return BoxUserSettings.find(
        Q('oauth_settings', 'ne', None)
    )


def get_authorized_node_settings(user_addon):
    """Returns node settings authorized by a given user settings object"""
    return BoxNodeSettings.find(
        Q('user_settings', 'eq', user_addon)
    )


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    with TokuTransaction():
        do_migration(get_targets(), dry=dry)


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
