#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate addongithubusersettings and create and attach addongithuboauthsettings.

Log:

    Executed on production by SL on 2014-10-05 at 23:11 EST. 269 AddonGithubUserSettings records
    were successfully migrated. 3 records with invalidated credentials were skipped.

    Script was modified by @chennan47 to handle records with invalidated credentials by unsetting
    the oauth_access_token, oauth_token_type, and github_user fields. Run on production by @sloria
    on 2014-10-07 at 12:34 EST. 3 records with invalidated credentials were migrated.
"""

import sys
import mock

from nose.tools import *
import github3

from framework.mongo import database
from website.app import init_app
from tests.base import OsfTestCase


from website.addons.github.api import GitHub
from website.addons.github.model import AddonGitHubOauthSettings, AddonGitHubUserSettings


def do_migration(records, dry=True):
    count, inval_cred_handled = 0, 0

    for raw_user_settings in records:

        # False if missing, None if field exists
        access_token = raw_user_settings.get('oauth_access_token', False)
        token_type = raw_user_settings.get('oauth_token_type', False)
        github_user_name = raw_user_settings.get('github_user', False)

        if access_token and token_type and github_user_name:
            if not dry:
                gh = GitHub(access_token, token_type)
                try:
                    github_user = gh.user()
                except github3.models.GitHubError:
                    AddonGitHubUserSettings._storage[0].store.update(
                        {'_id': raw_user_settings['_id']},
                        {
                            '$unset': {
                                "oauth_access_token" : True,
                                "oauth_token_type" : True,
                                "github_user" : True,
                            },
                        }
                    )
                    inval_cred_handled += 1
                    print('invalidated credentials handled record: {}'.format(raw_user_settings['_id']))
                    continue


                oauth_settings = AddonGitHubOauthSettings()
                oauth_settings.github_user_id = str(github_user.id)
                oauth_settings.save()
                oauth_settings.oauth_access_token = access_token
                oauth_settings.oauth_token_type = token_type
                oauth_settings.github_user_name = github_user_name
                oauth_settings.save()

                AddonGitHubUserSettings._storage[0].store.update(
                    {'_id': raw_user_settings['_id']},
                    {
                        '$unset': {
                            'oauth_access_token': True,
                            'oauth_token_type': True,
                            'github_user': True,
                        },
                        '$set': {
                            'oauth_settings': oauth_settings.github_user_id,
                        }
                    }
                )

                AddonGitHubOauthSettings._storage[0].store.update(
                    {'github_user_id': oauth_settings.github_user_id},
                    {
                        '$push': {
                            '__backrefs.accessed.addongithubusersettings.oauth_settings': raw_user_settings['_id'],
                        }
                    }
                )
                print('Finished migrating AddonGithubUserSettings record: {}'.format(raw_user_settings['_id']))
            count += 1
        # Old fields have not yet been unset
        elif None in set([access_token, token_type, github_user_name]):
            if not dry:
                AddonGitHubUserSettings._storage[0].store.update(
                    {'_id': raw_user_settings['_id']},
                    {
                        '$unset': {
                            'oauth_access_token': True,
                            'oauth_token_type': True,
                            'github_user': True,
                        },
                    }
                )
                print('Unset oauth_access_token and oauth_token_type: {0}'.format(raw_user_settings['_id']))
            count += 1

    return count, inval_cred_handled

def get_user_settings():
    # ... return the StoredObjects to migrate ...
    return database.addongithubusersettings.find()

def main():
    init_app('website.settings', set_backends=True, routes=True)  # Sets the storage backends on all models
    user_settings = get_user_settings()
    n_migrated, n_inval_cred_handled = do_migration(user_settings, dry='dry' in sys.argv)
    print("Total migrated records: {}".format(n_migrated))
    print("Total invalidated credentials handled records: {}".format(n_inval_cred_handled))


class TestMigrateGitHubOauthSettings(OsfTestCase):

    def setUp(self):
        super(TestMigrateGitHubOauthSettings, self).setUp()

        self.mongo_collection = database.addongithubusersettings
        self.user_settings = {
            "__backrefs" : {
                "authorized" : {
                    "addongithubnodesettings" : {
                        "user_settings" : [
                            "678910",
                        ]
                    }
                }
            },
            "_id" : "123456",
            "_version" : 1,
            "deletedAddonGitHubUserSettings" : False,
            "github_user" : "testing user",
            "oauth_access_token" : "testing acess token",
            "oauth_state" : "no state",
            "oauth_token_type" : "testing token type",
            "owner" : "abcde"
        }
        self.mongo_collection.insert(self.user_settings)

    def test_get_user_settings(self):

        records = list(get_user_settings())

        assert_equal(1, len(records))
        assert_equal(
            records[0]['github_user'],
            self.user_settings['github_user']
        )
        assert_equal(
            records[0]['oauth_state'],
            self.user_settings['oauth_state']
        )
        assert_equal(
            records[0]['oauth_access_token'],
            self.user_settings['oauth_access_token']
        )
        assert_equal(
            records[0]['oauth_token_type'],
            self.user_settings['oauth_token_type']
        )

    @mock.patch('website.addons.github.api.GitHub.user')
    def test_do_migration(self, mock_github_user):
        user = mock.Mock()
        user.id = "testing user id"
        mock_github_user.return_value = user
        do_migration(get_user_settings())
        user_settings = AddonGitHubUserSettings.find()[0]
        assert_true(user_settings.oauth_settings)
        assert_true(user_settings.oauth_state)
        assert_equal(
            user_settings.oauth_settings.github_user_name,
            "testing user"
        )
        assert_equal(
            user_settings.oauth_settings.oauth_access_token,
            "testing acess token"
        )
        assert_equal(
            user_settings.oauth_settings.oauth_token_type,
            "testing token type"
        )
        assert_equal(
            user_settings.oauth_settings.github_user_id,
            "testing user id"
        )

    def tearDown(self):
        self.mongo_collection.remove()

if __name__ == '__main__':
    main()
