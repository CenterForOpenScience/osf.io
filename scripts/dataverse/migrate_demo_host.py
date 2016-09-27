#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to migrate dataverse ExternalAccounts connected to the dataverse demo server.

"""

import sys
import logging
from modularodm import Q

from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

from website.oauth.models import ExternalAccount

logger = logging.getLogger(__name__)

OLD_HOST = 'dataverse-demo.iq.harvard.edu'
NEW_HOST = 'demo.dataverse.org'

def migrate(dry_run=True):
    migrated_accounts = []
    migrations_failed = {}
    for account in get_targets():
        try:
            account.display_name = NEW_HOST
            account.oauth_key = NEW_HOST
            account.save()
            migrated_accounts.append(account._id)
        except Exception as e:
            migrations_failed[account._id] = e

    if migrated_accounts:
        logging.info('Successfully migrated {0} ExcternalAccounts:\n{1}'.format(
            len(migrated_accounts), [e for e in migrated_accounts]
            )
        )

    if migrations_failed:
        logging.error('Failed to migrate {0} ExternalAccounts:\n{1}'.format(
            len(migrations_failed), ['{}: {}\n'.format(i, migrations_failed[i]) for i in migrations_failed.keys()]
            )
        )

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')

def get_targets():
    return ExternalAccount.find(
        Q('provider', 'eq', 'dataverse') &
        (Q('display_name', 'eq', OLD_HOST) | Q('oauth_key', 'eq', OLD_HOST))
    )

def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run=dry_run)

if __name__ == '__main__':
    main()
