# -*- coding: utf-8 -*-
"""Migration to add the correct provider_name for Zotero and Mendeley ExternalAccounts that
are missing it.
"""
import sys
import logging
from scripts import utils as scripts_utils

from modularodm import Q

from website.app import init_app
from website.models import ExternalAccount

logger = logging.getLogger(__name__)

def get_targets():
    return ExternalAccount.find(Q('provider', 'eq', 'zotero') | Q('provider', 'eq', 'mendeley'))


name_map = {
    'zotero': 'Zotero',
    'mendeley': 'Mendeley',
}

def migrate_extaccount(acct, dry=True):
    if not acct.provider_name:
        logger.info('Missing provider name for ExternalAccount {}'.format(acct._id))
        provider_name = name_map[acct.provider]
        logger.info('setting to {}'.format(acct._id))
        if not dry:
            acct.provider_name = provider_name
            acct.save()
        return True
    return False


def main(dry=True):
    count = 0
    for each in get_targets():
        migrated = migrate_extaccount(each, dry=dry)
        if migrated:
            count += 1
    logger.info('Migrated {} ExternalAccounts'.format(count))

if __name__ == '__main__':
    dry = 'dry' in sys.argv
    # Log to file
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    main(dry=dry)
