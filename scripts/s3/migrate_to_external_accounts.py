import logging
import os
import sys
import urlparse

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website import settings
from website.app import init_app
from website.models import User, Node
from website.oauth.models import ExternalAccount
from website.addons.s3 import settings as s3_settings
from website.addons.s3 import utils
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

PROVIDER = 's3'
PROVIDER_NAME = 'Amazon S3'
ENCRYPT_UPLOADS = s3_settings.ENCRYPT_UPLOADS_DEFAULT


def verify_user_settings_documents(user_document):
    try:
        assert('_id' in user_document)
        assert('deleted' in user_document)
        assert('owner' in user_document)
        assert('access_key' in user_document)
        assert('secret_key' in user_document)
        assert(user_document.get('owner', None))
    except AssertionError:
        return False
    else:
        return True

def verify_node_settings_document(document):
    try:    
        assert('_id' in document)
        assert('deleted' in document)
        assert('bucket' in document)
        assert('owner' in document)
        assert('user_settings' in document)
        assert(document.get('owner', None))
    except AssertionError:
        return False
    try:
        assert('encrypt_uploads' in document)
    except AssertionError:
        try:
            database['addons3nodesettings'].find_and_modify(
                {'_id': document['_id']},
                {
                    '$set': {
                        'encrypt_uploads': ENCRYPT_UPLOADS,
                    }
                }
            )
        except Exception:
            return False
    return True

def migrate_to_external_account(user_settings_document):
    user_info = utils.get_user_info(access_key=user_settings_document['access_key'], secret_key=user_settings_document['secret_key'])
    user = User.load(user_settings_document['owner'])
    if not user_info:
        return (None, None, None)

    new = False
    try:
        external_account = ExternalAccount.find_one(Q('provider_id', 'eq', user_info.id))
        logger.info('Duplicate account use found: s3usersettings {0} with id {1}'.format(user_settings_document['_id'], user._id))
    except NoResultsFound:
        new = True
        external_account = ExternalAccount(
            provider=PROVIDER,
            provider_name=PROVIDER_NAME,
            provider_id=user_info.id,
            oauth_key=user_settings_document['access_key'],
            oauth_secret=user_settings_document['secret_key'],
            display_name=user_info.display_name,
        )
        external_account.save()

    user.external_accounts.append(external_account)
    user.save()
    return external_account, user, new

def make_new_user_settings(user):
    # kill backrefs to old models
    database['user'].find_and_modify(
        {'_id': user._id},
        {
            '$unset': {
                '__backrefs.addons.addons3usersettings': ''
            }
        }
    )
    user.reload()
    return user.get_or_add_addon('s3', override=True)

def make_new_node_settings(node, node_settings_document, external_account=None, user_settings_instance=None):
    # kill backrefs to old models
    database['node'].find_and_modify(
        {'_id': node._id},
        {
            '$unset': {
                '__backrefs.addons.addons3nodesettings': ''
            }
        }
    )
    node.reload()
    node_settings_instance = node.get_or_add_addon('s3', auth=None, override=True, log=False)
    node_settings_instance.bucket = node_settings_document['bucket']
    node_settings_instance.save()
    if external_account and user_settings_instance:
        node_settings_instance.set_auth(
            external_account,
            user_settings_instance.owner,
            log=False
        )
    return node_settings_instance

def migrate(dry_run=True):
    user_settings_list = list(database['addons3usersettings'].find())

    # get in-memory versions of collections and collection sizes
    old_user_settings_collection = database['addons3usersettings']
    old_user_settings_count = old_user_settings_collection.count()
    old_node_settings_collection = database['addons3nodesettings']
    old_node_settings_count = old_node_settings_collection.count()

    # Lists of IDs for logging purposes
    external_accounts_created = []
    migrated_user_settings = []
    migrated_node_settings = []
    deleted_user_settings = []
    broken_user_settings = []
    user_no_oauth_creds = []
    invalid_oauth_creds = []
    inactive_user_or_no_owner = []
    unverifiable_node_settings = []
    deleted_node_settings = []
    nodeless_node_settings = []
    duped_accounts = {}
    dupe_count = 0

    for user_settings_document in user_settings_list:
        if user_settings_document['deleted']:
            logger.info(
                "Found addons3usersettings document (id:{0}) that is marked as deleted. It will not be migrated".format(user_settings_document['_id'])
            )
            deleted_user_settings.append(user_settings_document['_id'])
            continue
        if not verify_user_settings_documents(user_settings_document):
            logger.info(
                "Found broken addons3usersettings document (id:{0}) that could not be fixed.".format(user_settings_document['_id'])
            )
            broken_user_settings.append(user_settings_document['_id'])
            continue
        if not user_settings_document['access_key'] or not user_settings_document['secret_key']:
            logger.info(
                "Found addons3usersettings document (id:{0}) with incomplete or no oauth credentials. It will not be migrated.".format(user_settings_document['_id'])
            )
            user_no_oauth_creds.append(user_settings_document['_id'])
            continue
        external_account, user, new = migrate_to_external_account(user_settings_document)
        if not external_account:
            invalid_oauth_creds.append(user_settings_document['_id'])
            logger.warn('AddonS3UserSettings<{}> has invalid credentials. It will not be migrated'.format(
                user_settings_document['_id']
            ))
            continue
        if new:
            external_accounts_created.append(external_account._id)
        else:
            try:
                duped_accounts[external_account._id].append(user_settings_document['_id'])
            except KeyError:
                duped_accounts[external_account._id] = [user_settings_document['_id']]
            finally:
                dupe_count += 1
        linked_node_settings_documents = old_node_settings_collection.find({
            'user_settings': user_settings_document['_id']
        })
        if not user or not user.is_active:
            if linked_node_settings_documents.count() and not user.is_merged:
                logger.warn("AddonS3UserSettings<_id:{0}> has no owner, but is used by AddonS3NodeSettings: {1}.".format(
                    user_settings_document['_id'],
                    ', '.join([each['_id'] for each in linked_node_settings_documents])
                ))
                raise RuntimeError("This should never happen.")
            else:
                logger.info("AddonS3UserSettings<_id:{0}> either has no owner or the owner's account is not active, and will not be migrated.".format(
                    user_settings_document['_id']
                ))
                inactive_user_or_no_owner.append(user_settings_document['_id'])
                continue
        else:
            user_settings_instance = make_new_user_settings(user)
            for node_settings_document in linked_node_settings_documents:
                if not verify_node_settings_document(node_settings_document):
                    logger.info(
                        "Found addons3nodesettings document (id:{0}) that could not be verified. It will not be migrated.".format(
                            node_settings_document['_id'],
                        )
                    )
                    unverifiable_node_settings.append((node_settings_document['_id']))
                    continue
                if node_settings_document['deleted']:
                    logger.info(
                        "Found addons3nodesettings document (id:{0}) that is marked as deleted.".format(
                            node_settings_document['_id'],
                        )
                    )
                    deleted_node_settings.append(node_settings_document['_id'])
                    continue
                node = Node.load(node_settings_document['owner'])
                if not node:
                    logger.info("AddonS3NodeSettings<_id:{0}> has no associated Node, and will not be migrated.".format(
                        node_settings_document['_id']
                    ))
                    nodeless_node_settings.append(node_settings_document['_id'])
                    continue
                else:
                    node_settings_document = database['addons3nodesettings'].find_one({'_id': node_settings_document['_id']})
                    make_new_node_settings(
                        node,
                        node_settings_document,
                        external_account,
                        user_settings_instance
                    )
                    migrated_node_settings.append(node_settings_document['_id'])
        migrated_user_settings.append(user_settings_document['_id'])

    logger.info(
        "Created {0} new external accounts from {1} old user settings documents:\n{2}".format(
            len(external_accounts_created), old_user_settings_count, [e for e in external_accounts_created]
        )
    )
    logger.info(
        "Successfully migrated {0} user settings from {1} old user settings documents:\n{2}".format(
            len(migrated_user_settings), old_user_settings_count, [e for e in migrated_user_settings]
        )
    )
    logger.info(
        "Successfully migrated {0} node settings from {1} old node settings documents:\n{2}".format(
            len(migrated_node_settings), old_node_settings_count, [e for e in migrated_node_settings]
        )
    )

    if duped_accounts:
        logger.info(
            "Found {0} cases of duplicate account use across {1} addons3usersettings, causing ExternalAccounts to not be created for {2} user settings.\n\
            Note that original linked user settings are excluded from this list:\n{3}".format(
                len(duped_accounts),
                len(duped_accounts) + dupe_count,
                dupe_count,
                ['{}: {}'.format(e, duped_accounts[e]) for e in duped_accounts.keys()]
            )
        )

    if user_no_oauth_creds:
        logger.warn(
            "Skipped migration of {0} invalid user settings with a lack of oauth credentials:\n{1}".format(
                len(user_no_oauth_creds), [e for e in user_no_oauth_creds]
            )
        )
    if invalid_oauth_creds:
        logger.warn(
            "Skipped migration of {0} user settings due to invalid oauth credentials:\n{1}".format(
                len(invalid_oauth_creds), [e for e in invalid_oauth_creds]
            )
        )
    if deleted_user_settings:
        logger.warn(
            "Skipped migration of {0} deleted user settings: {1}".format(
                len(deleted_user_settings), [e for e in deleted_user_settings]
            )
        )
    if broken_user_settings:
        logger.warn(
            "Skipped migration of {0} addons3usersettings because they could not be verified:\n{1}".format(
                len(broken_user_settings), [e for e in broken_user_settings]
            )
        )
    if inactive_user_or_no_owner:
        logger.warn(
            "Skipped migration of {0} user settings due to an inactive or null owner:\n{1}".format(
                len(inactive_user_or_no_owner), [e for e in inactive_user_or_no_owner]
            )
        )
    if unverifiable_node_settings:
        logger.warn(
            "Skipped migration of {0} addons3nodesettings documents because they could not be verified:\n{1}".format(
                len(unverifiable_node_settings), [e for e in unverifiable_node_settings]
            )
        )
    if deleted_node_settings:
        logger.warn(
            "Skipped migration of {0} deleted node settings:\n{1}".format(
                len(deleted_node_settings), [e for e in deleted_node_settings]
            )
        )
    if nodeless_node_settings:
        logger.warn(
            "Skipped migration of {0} node settings without an associated node:\n{1}".format(
                len(nodeless_node_settings), [e for e in nodeless_node_settings]
            )
        )

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')


def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run=dry_run)

if __name__ == "__main__":
    main()