#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to migrate Dataverse credentials from user settings object to external
account objects.

Changes:
 - Include configurable `host` in Dataverse settings
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

from website.addons.dataverse.model import AddonDataverseUserSettings
from website.addons.dataverse.model import AddonDataverseNodeSettings
from website.oauth.models import ExternalAccount

logger = logging.getLogger(__name__)


def do_migration(records, dry=True):
    host = 'dataverse.harvard.edu'

    for user_addon in records:

        user = user_addon.owner
        api_token = user_addon.api_token

        with TokuTransaction():
            logger.info('Record found for user {}'.format(user._id))

            if not dry:

                # Modified from `dataverse_add_user_account`
                # Create/load external account and append to user
                try:
                    account = ExternalAccount(
                        provider='dataverse',
                        provider_name='Dataverse',
                        display_name=host,
                        oauth_key=host,
                        oauth_secret=api_token,
                        provider_id=api_token,
                    )
                    account.save()
                except KeyExistsException:
                    # ... or get the old one
                    account = ExternalAccount.find_one(
                        Q('provider', 'eq', 'dataverse') &
                        Q('provider_id', 'eq', api_token)
                    )
                    assert account is not None
                user.external_accounts.append(account)
                user.save()

                # Remove api_token from user settings object
                user_addon.api_token = None
                user_addon.save()

                logger.info('Added external account {0} to user {1}'.format(
                    account._id, user._id,
                ))

                # Add external account to authorized nodes
                for node_addon in get_authorized_node_settings(user_addon):
                    node_addon.set_auth(account, user)

                    logger.info('Added external account {0} to node {1}'.format(
                        account._id, node_addon.owner._id,
                    ))


def get_targets():
    return AddonDataverseUserSettings.find(
        Q('api_token', 'ne', None)
    )


def get_authorized_node_settings(user_addon):
    """Returns node settings authorized by a given user settings object"""
    return AddonDataverseNodeSettings.find(
        Q('user_settings', 'eq', user_addon)
    )


def main(dry=True):
    init_app(set_backends=True, routes=False, mfr=False)  # Sets the storage backends on all models
    do_migration(get_targets(), dry=dry)


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
