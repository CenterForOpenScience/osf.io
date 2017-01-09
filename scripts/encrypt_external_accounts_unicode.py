import logging
import sys

import jwe

from framework.encryption import SENSITIVE_DATA_KEY
from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def verify_external_account(document):
    assert '_id' in document, 'ExternalAccount {} has no _id'.format(document)
    assert 'provider' in document, 'ExternalAccount {} has no provider'.format(document['_id'])
    assert 'oauth_key' in document, 'ExternalAccount {} has no oauth_key'.format(document['_id'])
    assert 'oauth_secret' in document, 'ExternalAccount {} has no oauth_secret'.format(document['_id'])
    assert 'display_name' in document, 'ExternalAccount {} has no display_name'.format(document['_id'])

def encrypt_key(document, key):
    database['externalaccount'].find_and_modify(
        {'_id': document['_id']},
        {'$set': {
            key: jwe.encrypt(bytes(jwe.decrypt(document[key].encode('utf-8'), SENSITIVE_DATA_KEY)), SENSITIVE_DATA_KEY)
        }})

def migrate(dry_run=True):
    external_accounts = list(database['externalaccount'].find())
    keys = ['oauth_key', 'oauth_secret', 'refresh_token', 'display_name', 'profile_url']

    provider_key_count_map = {key: {} for key in keys}

    logger.info('Preparing to migrate {} ExternalAccounts'.format(len(external_accounts)))

    for account in external_accounts:
        verify_external_account(account)
        for key in keys:
            if account.get(key) is not None:
                logger.info('Migrating {} for {}:{}'.format(key, account['provider'], account['_id']))
                encrypt_key(account, key)
                if account['provider'] not in provider_key_count_map[key]:
                    provider_key_count_map[key][account['provider']] = 0
                provider_key_count_map[key][account['provider']] += 1

    for key in provider_key_count_map:
        for provider in provider_key_count_map[key]:
            count = provider_key_count_map[key][provider]
            logger.info('Migrated {} for {} {} accounts'.format(key, count, provider))

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run=dry_run)
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')

if __name__ == "__main__":
    main()
