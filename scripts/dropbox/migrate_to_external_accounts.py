import logging
import os
import sys
import shutil

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website import settings
dropbox_views_path = os.path.join(
    settings.BASE_PATH,
    'addons',
    'dropbox',
    'views'
)
if os.path.isdir(dropbox_views_path):
    shutil.rmtree(dropbox_views_path)

from website.app import init_app
from website.models import User, Node
from website.oauth.models import ExternalAccount
from website.addons.dropbox.model import (
    DropboxNodeSettings,
    DropboxUserSettings
)

logger = logging.getLogger(__name__)

PROVIDER = 'dropbox'
PROVIDER_NAME = 'Dropbox'

def verify_user_settings_document(document):
    assert '_id' in document
    assert 'deleted' in document
    assert not document['deleted']
    assert 'access_token' in document
    assert 'dropbox_id' in document
    if document['access_token']:
        assert document['dropbox_id'] is not None
    assert 'dropbox_info' in document
    assert 'display_name' in document['dropbox_info']
    assert 'owner' in document
    assert document['owner'] is not None

def verify_node_settings_document(document):
    assert '_id' in document
    assert 'deleted' in document
    assert not document['deleted']
    assert 'folder' in document
    assert 'owner' in document
    assert document['owner'] is not None
    assert 'user_settings' in document

def migrate_to_external_account(user_settings_document, user):
    if not user_settings_document.get('access_token'):
        return None
    user = User.load(user_settings_document['owner'])
    external_account = ExternalAccount(
        provider=PROVIDER,
        provider_name=PROVIDER_NAME,
        oauth_key=user_settings_document['access_token'],
        display_name=user_settings_document['dropbox_info'].get('display_name', None),
    )
    external_account.save()  # generate pk for external account
    user.external_accounts.append(external_account)
    user.save()
    return external_account, user

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
    return user.add_addon('dropbox', override=True)

def make_new_node_settings(node, node_settings_document, external_account, user_settings_instance):
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
    node_settings_instance = node.add_addon('dropbox', override=True)
    node_settings_instance.folder = node_settings_document['folder']
    node_settings_instance.save()
    node_settings_instance.set_auth(
        external_account,
        user_settings_instance.owner,
        log=False
    )

def remove_old_documents(old_user_settings, old_node_settings):
    logger.info('Removing {0} old dropboxusersettings documents'.format(
        old_user_settings.count()
    ))
    database['dropboxusersettings'].remove({
        '_id': {
            '$in': map(lambda s: s['_id'], old_user_settings)
        }
    })
    logger.info('Removing {0} old dropboxnodesettings documents'.format(
        old_node_settings.count()
    ))
    database['dropboxnodesettings'].remove({
        '_id': {
            '$in': map(lambda s: s['_id'], old_node_settings)
        }
    })

def migrate(dry_run=True):
    user_settings_list = list(database['dropboxusersettings'].find())

    old_user_settings = database['dropboxusersettings'].find()
    old_node_settings = database['dropboxnodesettings'].find()

    external_accounts_created = 0
    migrated_user_settings = 0
    migrated_node_settings = 0    
    for user_settings_document in user_settings_list:
        try:
            verify_user_settings_document(user_settings_document)
        except AssertionError:
            raise RuntimeError(
                "Invalid dropboxusersettings document (_id:{0}) found. Aborting migration.".format(user_settings_document['_id'])
            )
        if not dry_run:
            external_account, user = migrate_to_external_account(user_settings_document)
            if not external_account:
                logger.info("DropboxUserSettings<_id:{0}> has no oauth credentials and will not be migrated.".format(
                    user_settings_document['_id']
                ))
            else:
                external_accounts_created += 1
                linked_node_settings_documents = database['dropboxnodesettings'].find({
                    'user_settings': user_settings_document['_id']
                })
                if not user or not user.is_active:
                    if linked_node_settings_documents.count():
                        logger.warn("DropboxUserSettings<_id:{0}> has no owner, but is used by DropboxNodeSettings: {1}.".format(
                            user_settings_document['_id'],
                            ', '.join(linked_node_settings_documents.map(lambda d: d['_id']))
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
                        try:
                            verify_node_settings_document(node_settings_document)
                        except AssertionError:
                            raise RuntimeError(
                                "Invalid dropboxnodesettings document found (_id:{0}). Aborting migration.".format(node_settings_document['_id'])
                            )
                        node = Node.load(node_settings_document['owner'])
                        if not node:
                            logger.info("DropboxNodeSettings<_id:{0}> either has no associated Node, and will not be migrated.".format(
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
    remove_old_documents(old_user_settings, old_node_settings)
    if dry_run:
        raise RuntimeError('Dry run.')

def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    with TokuTransaction():
        migrate(dry_run=dry_run)

if __name__ == "__main__":
    main()
