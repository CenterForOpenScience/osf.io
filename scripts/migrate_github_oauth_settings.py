#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate nodes with invalid categories."""

import sys
import mock

from nose.tools import *

from framework.mongo import database
from website.app import init_app
from tests.base import OsfTestCase


from website.addons.github.api import GitHub
from website.addons.github.model import AddonGitHubOauthSettings, AddonGitHubUserSettings


# user_settings_collection = AddonGitHubUserSettings._storage[0].store

def do_migration(records):
    # ... perform the migration ...
    
    for raw_user_settings in records:

        access_token = raw_user_settings['oauth_access_token']
        token_type = raw_user_settings['oauth_token_type']
        github_user_name = raw_user_settings['github_user']

        if access_token and token_type and github_user_name:
            gh = GitHub(access_token, token_type)
            github_user = gh.user()

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
        
def get_user_settings():
    # ... return the StoredObjects to migrate ...
    return database.addongithubusersettings.find()

def main():
    init_app('website.settings', set_backends=True, routes=True)  # Sets the storage backends on all models
    user_settings = get_user_settings()
    if 'dry' in sys.argv:
        # print list of affected nodes, totals, etc.
        for user_setting in user_settings:
            print "===AddonGithubUserSettings==="
            print "user_settings_id:"
            print (user_setting['_id'])

    else:
        do_migration(get_user_settings())


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
