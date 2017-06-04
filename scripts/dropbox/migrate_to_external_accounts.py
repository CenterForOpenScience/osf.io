import logging
import sys

from dropbox.client import DropboxClient
from nose.tools import *  # noqa
from modularodm import Q

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.models import User, Node
from website.oauth.models import ExternalAccount
from scripts import utils as script_utils


logger = logging.getLogger(__name__)

PROVIDER = 'dropbox'
PROVIDER_NAME = 'Dropbox'

def verify_user_settings_document(document):
    try:
        assert_in('_id', document)
        assert_in('deleted', document)
        assert_in('access_token', document)
        assert_in('dropbox_id', document)
        if document['access_token']:
            assert_is_not_none(document['dropbox_id'])
        assert_in('dropbox_info', document)
        assert_in('display_name', document['dropbox_info'])
        assert_in('owner', document)
        assert_is_not_none(document['owner'])
    except AssertionError:
        return salvage_broken_user_settings_document(document)
    else:
        return True

def verify_node_settings_document(document):
    assert_in('_id', document)
    assert_in('deleted', document)
    assert_in('folder', document)
    assert_in('owner', document)
    assert_is_not_none(document['owner'])
    assert_in('user_settings', document)

def salvage_broken_user_settings_document(document):
    if not document['access_token'] or not document['dropbox_id']:
        return False
    if not document['owner'] or not User.load(document['owner']).is_active:
        return False
    if document['deleted']:
        return False
    if not document.get('dropbox_info') or not document['dropbox_info']['display_name']:
        logger.info(
            "Attempting dropbox_info population for document (id:{0})".format(document['_id'])
        )
        client = DropboxClient(document['access_token'])
        document['dropbox_info'] = {}
        try:
            database['dropboxusersettings'].find_and_modify(
                {'_id': document['_id']},
                {
                    '$set': {
                        'dropbox_info': client.account_info()
                    }
                }
            )
        except Exception:
            # Invalid token probably
            # Still want Dropbox to be enabled to show error message
            # to user on node settings, pass
            return True
        else:
            return True

    return False

def migrate_to_external_account(user_settings_document):
    if not user_settings_document.get('access_token'):
        return (None, None, None)
    new = False
    user = User.load(user_settings_document['owner'])
    try:
        external_account = ExternalAccount.find(Q('provider_id', 'eq', user_settings_document['dropbox_id']))[0]
        logger.info('Duplicate account use found: User {0} with dropbox_id {1}'.format(user.username, user_settings_document['dropbox_id']))
    except IndexError:
        new = True
        external_account = ExternalAccount(
            provider=PROVIDER,
            provider_name=PROVIDER_NAME,
            provider_id=user_settings_document['dropbox_id'],
            oauth_key=user_settings_document['access_token'],
            display_name=user_settings_document['dropbox_info'].get('display_name', None) if user_settings_document.get('dropbox_info', None) else None,
        )
        external_account.save()  # generate pk for external accountc

    user.external_accounts.append(external_account)
    user.save()
    return external_account, user, new

def make_new_user_settings(user):
    # kill the old backrefs
    database['user'].find_and_modify(
        {'_id': user._id},
        {
            '$set': {
                '__backrefs.addons.dropboxusersettings.owner': []
            }
        }
    )
    user.reload()
    return user.get_or_add_addon('dropbox', override=True)

def make_new_node_settings(node, node_settings_document, external_account=None, user_settings_instance=None):
    # kill the old backrefs
    database['node'].find_and_modify(
        {'_id': node._id},
        {
            '$set': {
                '__backrefs.addons.dropboxnodesettings.owner': []
            }
        }
    )
    node.reload()
    node_settings_instance = node.get_or_add_addon('dropbox', auth=None, override=True, log=False)
    node_settings_instance.folder = node_settings_document['folder']
    node_settings_instance.save()
    if external_account and user_settings_instance:
        node_settings_instance.set_auth(
            external_account,
            user_settings_instance.owner,
            log=False
        )
    return node_settings_instance

def remove_old_documents(old_user_settings, old_user_settings_count, old_node_settings, old_node_settings_count, dry_run):
    logger.info('Removing {0} old dropboxusersettings documents'.format(
        old_user_settings_count
    ))
    if not dry_run:
        database['dropboxusersettings'].remove({
            '_id': {
                '$in': map(lambda s: s['_id'], old_user_settings)
            }
        })
    logger.info('Removing {0} old dropboxnodesettings documents'.format(
        old_node_settings_count
    ))
    if not dry_run:
        database['dropboxnodesettings'].remove({
            '_id': {
                '$in': map(lambda s: s['_id'], old_node_settings)
            }
        })

def migrate(dry_run=True, remove_old=True):
    rm_msg = ' It will be hard-deleted during the migration.' if remove_old else ''

    user_settings_list = list(database['dropboxusersettings'].find())

    # get in-memory versions of collections and collection sizes
    user_settings_collection = database['dropboxusersettings']
    old_user_settings = list(user_settings_collection.find())
    old_user_settings_count = user_settings_collection.count()
    node_settings_collection = database['dropboxnodesettings']
    old_node_settings = list(node_settings_collection.find())
    old_node_settings_count = node_settings_collection.count()

    external_accounts_created = 0
    migrated_user_settings = 0
    migrated_node_settings = 0
    for user_settings_document in user_settings_list:
        if not verify_user_settings_document(user_settings_document):
            logger.info(
                "Found broken dropboxusersettings document (id:{0}) that could not be fixed.{1}".format(user_settings_document['_id'], rm_msg)
            )
            continue
        if user_settings_document['deleted']:
            logger.info(
                "Found dropboxusersettings document (id:{0}) that is marked as deleted.{1}".format(user_settings_document['_id'], rm_msg)
            )
            continue
        user_settings_document = database['dropboxusersettings'].find_one({'_id': user_settings_document['_id']})
        external_account, user, new = migrate_to_external_account(user_settings_document)
        if not external_account:
            logger.info("DropboxUserSettings<_id:{0}> has no oauth credentials and will not be migrated.".format(
                user_settings_document['_id']
            ))
        else:
            if new:
                external_accounts_created += 1
            linked_node_settings_documents = database['dropboxnodesettings'].find({
                'user_settings': user_settings_document['_id']
            })
            if not user or not user.is_active:
                if linked_node_settings_documents.count() and not user.is_merged:
                    logger.warn("DropboxUserSettings<_id:{0}> has no owner, but is used by DropboxNodeSettings: {1}.".format(
                        user_settings_document['_id'],
                        ', '.join([each['_id'] for each in linked_node_settings_documents])
                    ))
                    raise RuntimeError("This should never happen.")
                else:
                    logger.info("DropboxUserSettings<_id:{0}> either has no owner or the owner's account is not active, and will not be migrated.".format(
                        user_settings_document['_id']
                    ))
                    continue
            else:
                user_settings_instance = make_new_user_settings(user)
                for node_settings_document in linked_node_settings_documents:
                    verify_node_settings_document(node_settings_document)
                    if node_settings_document['deleted']:
                        logger.info(
                            "Found dropboxnodesettings document (id:{0}) that is marked as deleted.{1}".format(
                                node_settings_document['_id'],
                                rm_msg
                            )
                        )
                        continue
                    node = Node.load(node_settings_document['owner'])
                    if not node:
                        logger.info("DropboxNodeSettings<_id:{0}> has no associated Node, and will not be migrated.".format(
                            node_settings_document['_id']
                        ))
                        continue
                    else:
                        make_new_node_settings(
                            node,
                            node_settings_document,
                            external_account,
                            user_settings_instance
                        )
                        migrated_node_settings += 1
        migrated_user_settings += 1
    logger.info(
        "Created {0} new external accounts, migrated {1} dropboxusersettings, and migrated {2} dropboxnodesettings.".format(
            external_accounts_created, migrated_user_settings, migrated_node_settings
        )
    )
    if remove_old:
        remove_old_documents(
            old_user_settings, old_user_settings_count,
            old_node_settings, old_node_settings_count,
            dry_run
        )

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')

def main():
    dry_run = False
    remove_old = True
    if '--keep' in sys.argv:
        remove_old = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run=dry_run, remove_old=remove_old)

if __name__ == "__main__":
    main()
