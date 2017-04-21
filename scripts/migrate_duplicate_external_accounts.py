from __future__ import absolute_import

import logging
import sys

from dropbox.rest import ErrorResponse
from dropbox.client import DropboxClient

from framework.mongo import database as db
from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.addons.github.api import GitHubClient
from website.addons.github.exceptions import GitHubError
from website.oauth.models import ExternalAccount
from scripts import utils as script_utils


logger = logging.getLogger(__name__)

def creds_are_valid(ea_id):
    logger.warn('Validating credentials for externalaccount {}'.format(ea_id))
    ea = ExternalAccount.load(ea_id)
    if ea.provider == 'github':
        try:
            GitHubClient(external_account=ea).user()
        except (GitHubError, IndexError):
            logger.info('Invalid creds: {}'.format(ea_id))
            return False
    elif ea.provider == 'dropbox':
        try:
            DropboxClient(ea.oauth_key).account_info()
        except (ValueError, IndexError, ErrorResponse):
            logger.info('Invalid creds: {}'.format(ea_id))
            return False
    else:
        raise Exception('Unexpected provider: {}'.format(ea.provider))
    logger.info('Valid creds: {}'.format(ea_id))
    return True

def swap_references_and_rm(to_keep, to_swap, provider):
    logger.info('Swapping {} references to {} with {}'.format(provider, to_swap, to_keep))
    db['{}nodesettings'.format(provider)].find_and_modify(
        {'external_account': to_swap},
        {'$set': {
            'external_account': to_keep
        }}
    )
    us_map = {us['_id']: us['external_accounts'] for us in db['{}usersettings'.format(provider)].find({'external_accounts': to_swap})}
    for usid, ealist in us_map.items():
        ealist.remove(to_swap)
        ealist.append(to_keep)
        db['{}usersettings'.format(provider)].find_and_modify(
            {'_id': usid},
            {'$set': {
                'external_accounts': ealist
            }}
        )
    u_map = {u['_id']: u['external_accounts'] for u in db['user'].find({'external_accounts': to_swap})}
    for uid, ealist in u_map.items():
        ealist.remove(to_swap)
        ealist.append(to_keep)
        db['user'].find_and_modify(
            {'_id': uid},
            {'$set': {
                'external_accounts': ealist
            }}
        )
    logger.info('Removing EA {}'.format(to_swap))
    db.externalaccount.remove({'_id': to_swap})

def migrate():
    possible_collisions = db.externalaccount.find({'provider_id': {'$type': 16}})

    pc_map = {'dropbox': [], 'github': [], 'figshare': []}
    for pc in possible_collisions:
        pc_map[pc['provider']].append(pc)

    collisions = []
    for provider in pc_map:
        for pc in pc_map[provider]:
            if db.externalaccount.find({'provider': provider, 'provider_id': str(pc['provider_id'])}).count():
                collisions.append([provider, pc['_id'], db.externalaccount.find_one({'provider': provider, 'provider_id': str(pc['provider_id'])})['_id']])

    ns_map = {'github': db.githubnodesettings, 'dropbox': db.dropboxnodesettings, 'figshare': db.figsharenodesettings}
    eas_no_ns = []
    for provider, int_ea, str_ea in collisions:
        if ns_map[provider].find({'external_account': int_ea}).count() == 0:
            eas_no_ns.append(int_ea)
            swap_references_and_rm(str_ea, int_ea, provider)
        elif ns_map[provider].find({'external_account': str_ea}).count() == 0:
            eas_no_ns.append(str_ea)
            swap_references_and_rm(int_ea, str_ea, provider)
        else:
            logger.info('{}nodesettings exist for both externalaccounts {} AND {}'.format(provider, int_ea, str_ea))
            if creds_are_valid(int_ea) and not creds_are_valid(str_ea):
                swap_references_and_rm(int_ea, str_ea, provider)
            else:
                swap_references_and_rm(str_ea, int_ea, provider)
    logger.info('Fixed {} external account collisions'.format(len(collisions)))

def main():
    dry = '--dry' in sys.argv
    script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate()
        if dry:
            raise RuntimeError('Dry run -- Transaction rolled back')

if __name__ == '__main__':
    main()
