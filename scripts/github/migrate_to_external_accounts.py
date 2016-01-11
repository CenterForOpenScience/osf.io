import logging
import os
import sys
import urlparse

from nose.tools import *  # noqa
from modularodm import Q

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from website import settings
from website.app import init_app
from website.models import User, Node
from website.oauth.models import ExternalAccount
from website.addons.github.api import GitHubClient
from website.addons.github import settings as github_settings
from website.addons.github.utils import make_hook_secret
from website.addons.github.exceptions import GitHubError
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

PROVIDER = 'github'
PROVIDER_NAME = 'GitHub'
HOOK_DOMAIN = github_settings.HOOK_DOMAIN or settings.DOMAIN

def verify_user_and_oauth_settings_documents(user_document, oauth_document):
    try:
        assert_in('_id', user_document)
        assert_in('oauth_settings', user_document)
        assert_in('deleted', user_document)
        assert_in('owner', user_document)
        assert_in('_id', oauth_document)
        assert_in('github_user_id', oauth_document)
        assert_in('github_user_name', oauth_document)
        assert_in('oauth_access_token', oauth_document)
        assert_is_not_none(user_document['owner'])
        assert_equal(user_document['oauth_settings'], oauth_document['github_user_id'])
    except AssertionError:
        return False
    else:
        return True

def verify_node_settings_document(document, account):
    assert_in('_id', document)
    assert_in('deleted', document)
    assert_in('hook_id', document)
    assert_in('repo', document)
    assert_in('user', document)
    assert_in('registration_data', document)
    assert_in('owner', document)
    assert_is_not_none(document['owner'])
    assert_in('user_settings', document)
    try:
        assert_in('hook_secret', document)
    except AssertionError:
        try:
            add_hook_to_old_node_settings(document, account)
        except GitHubError:
            return False
    return True

def add_hook_to_old_node_settings(document, account):
    connect = GitHubClient(external_account=account)
    secret = make_hook_secret()
    try:
        hook = connect.add_hook(
            document['user'], document['repo'],
            'web',
            {
                'url': urlparse.urljoin(
                    HOOK_DOMAIN,
                    os.path.join(
                        Node.load(document['owner']).api_url, 'github', 'hook/'
                    )
                ),
                'content_type': github_settings.HOOK_CONTENT_TYPE,
                'secret': secret,
            }
        )
    except GitHubError:
        raise

    if hook:
        database['addongithubnodesettings'].find_and_modify(
            {'_id': document['_id']},
            {
                '$set': {
                    'hook_id': hook.id,
                    'hook_secret': secret
                }
            }
        )
    else:
        raise GitHubError

def migrate_to_external_account(user_settings_document, oauth_settings_document):
    if not oauth_settings_document.get('oauth_access_token'):
        return (None, None, None)
    new = False
    user = User.load(user_settings_document['owner'])
    try:
        external_account = ExternalAccount.find(Q('provider_id', 'eq', oauth_settings_document['github_user_id']))[0]
        logger.info('Duplicate account use found: User {0} with github_user_id {1}'.format(user.username, oauth_settings_document['github_user_id']))
    except IndexError:
        new = True
        external_account = ExternalAccount(
            provider=PROVIDER,
            provider_name=PROVIDER_NAME,
            provider_id=oauth_settings_document['github_user_id'],
            oauth_key=oauth_settings_document['oauth_access_token'],
            display_name=oauth_settings_document['github_user_name'],
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
                '__backrefs.addons.addongithubusersettings': ''
            }
        }
    )
    user.reload()
    return user.get_or_add_addon('github', override=True)

def make_new_node_settings(node, node_settings_document, external_account=None, user_settings_instance=None):
    # kill backrefs to old models
    database['node'].find_and_modify(
        {'_id': node._id},
        {
            '$unset': {
                '__backrefs.addons.addongithubnodesettings': ''
            }
        }
    )
    node.reload()
    node_settings_instance = node.get_or_add_addon('github', auth=None, override=True, log=False)
    node_settings_instance.repo = node_settings_document['repo']
    node_settings_instance.user = node_settings_document['user']
    node_settings_instance.hook_id = node_settings_document['hook_id']
    node_settings_instance.hook_secret = node_settings_document['hook_secret']
    node_settings_instance.registration_data = node_settings_document['registration_data']
    node_settings_instance.save()
    if external_account and user_settings_instance:
        node_settings_instance.set_auth(
            external_account,
            user_settings_instance.owner,
            log=False
        )
    return node_settings_instance

def migrate(dry_run=True):
    user_settings_list = list(database['addongithubusersettings'].find())

    # get in-memory versions of collections and collection sizes
    old_user_settings_collection = database['addongithubusersettings']
    old_user_settings = list(old_user_settings_collection.find())
    old_user_settings_count = old_user_settings_collection.count()
    old_node_settings_collection = database['addongithubnodesettings']
    old_node_settings = list(old_node_settings_collection.find())
    old_node_settings_count = old_node_settings_collection.count()
    old_oauth_settings_collection = database['addongithuboauthsettings']
    old_oauth_settings = list(old_oauth_settings_collection.find())
    old_oauth_settings_count = old_oauth_settings_collection.count()


    external_accounts_created = 0 
    migrated_user_settings = 0
    migrated_node_settings = 0

    for user_settings_document in user_settings_list:
        try:
            oauth_settings_document = old_oauth_settings_collection.find_one({'github_user_id': user_settings_document['oauth_settings']})
        except KeyError:
            pass
        if not oauth_settings_document:
            logger.info(
                "Found addongithubusersettings document (id:{0}) with no associated oauth_settings. It will not be migrated.".format(user_settings_document['_id'])
            )
            continue
        if user_settings_document['deleted']:
            logger.info(
                "Found addongithubusersettings document (id:{0}) that is marked as deleted.".format(user_settings_document['_id'])
            )
            continue
        if not verify_user_and_oauth_settings_documents(user_settings_document, oauth_settings_document):
            logger.info(
                "Found broken addongithubusersettings document (id:{0}) that could not be fixed.".format(user_settings_document['_id'])
            )
            continue
        external_account, user, new = migrate_to_external_account(user_settings_document, oauth_settings_document)
        if not external_account:
            logger.info("AddonGitHubUserSettings<_id:{0}> has no oauth credentials and will not be migrated.".format(
                user_settings_document['_id']
            ))
        else:
            if new:
                external_accounts_created += 1
            linked_node_settings_documents = old_node_settings_collection.find({
                'user_settings': user_settings_document['_id']
            })
            if not user or not user.is_active:
                if linked_node_settings_documents.count() and not user.is_merged:
                    logger.warn("AddonGitHubUserSettings<_id:{0}> has no owner, but is used by AddonGitHubNodeSettings: {1}.".format(
                        user_settings_document['_id'],
                        ', '.join([each['_id'] for each in linked_node_settings_documents])
                    ))
                    raise RuntimeError("This should never happen.")
                else:
                    logger.info("AddonGitHubUserSettings<_id:{0}> either has no owner or the owner's account is not active, and will not be migrated.".format(
                        user_settings_document['_id']
                    ))
                    continue
            else:
                user_settings_instance = make_new_user_settings(user)
                for node_settings_document in linked_node_settings_documents:
                    if not verify_node_settings_document(node_settings_document, external_account):
                        logger.info(
                            "Found addongithubnodesettings document (id:{0}) that could not be verified. It will not be migrated.".format(
                                node_settings_document['_id'],
                            )
                        )
                        continue
                    if node_settings_document['deleted']:
                        logger.info(
                            "Found addongithubnodesettings document (id:{0}) that is marked as deleted.".format(
                                node_settings_document['_id'],
                            )
                        )
                        continue
                    node = Node.load(node_settings_document['owner'])
                    if not node:
                        logger.info("AddonGitHubNodeSettings<_id:{0}> has no associated Node, and will not be migrated.".format(
                            node_settings_document['_id']
                        ))
                        continue
                    else:
                        node_settings_document = database['addongithubnodesettings'].find_one({'_id': node_settings_document['_id']})
                        make_new_node_settings(
                            node,
                            node_settings_document,
                            external_account,
                            user_settings_instance
                        )
                        migrated_node_settings += 1
        migrated_user_settings += 1
    logger.info(
        "Created {0} new external accounts, migrated {1} githubusersettings, and migrated {2} githubnodesettings.".format(
            external_accounts_created, migrated_user_settings, migrated_node_settings
        )
    )

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back.')


def main():
    dry_run = False
    remove_old = True
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(dry_run=dry_run)

if __name__ == "__main__":
    main()
