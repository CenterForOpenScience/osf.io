#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate nodes with invalid categories."""

import sys
import mock
from modularodm import Q
from website.app import init_app
from tests.base import OsfTestCase

from framework.auth import User
from website.addons.github.api import GitHub
from website.addons.github.model import AddonGitHubOauthSettings, AddonGitHubUserSettings


def do_migration(records):
    # ... perform the migration ...
    
    for user_settings in records:
        
        access_token = user_settings.oauth_access_token
        token_type = user_settings.oauth_token_type
        github_user_name = user_settings.github_user
        
        gh = GitHub(access_token, token_type)
        github_user = gh.user()

        oauth_settings = AddonGitHubOauthSettings()
        oauth_settings.github_user_id = str(github_user.id)
        oauth_settings.oauth_access_token = access_token
        oauth_settings.oauth_token_type = token_type
        oauth_settings.github_user_name = github_user_name
        oauth_settings.save()
        
        del user_settings.oauth_access_token
        del user_settings.oauth_token_type
        del user_settings.github_user
        user_settings.oauth_settings = oauth_settings
        user_settings.save()
        
        
def get_user_settings():
    # ... return the StoredObjects to migrate ...
    return AddonGitHubUserSettings.find()

def main():
    init_app(set_backends=True, routes=True)  # Sets the storage backends on all models
    user_settings = get_user_settings()
    if 'dry' in sys.argv:
        # print list of affected nodes, totals, etc.
        for user_setting in user_settings:
            print "===AddonGithubUserSettings==="
            print "github_user:"
            print (user_setting.github_user)

    else:
        do_migration(get_user_settings())


class TestMigrateGitHubOauthSettings(OsfTestCase):
    def setUp(self):
        super(TestMigrateGitHubOauthSettings, self).setUp()
        self.user_settings = AddonGitHubUserSettings()
        self.user_settings._id = "testing user settings"
        self.user_settings.save()
        self.user_settings.oauth_access_token = "testing acess token"
        self.user_settings.oauth_token_type = "testing token type"
        self.user_settings.oauth_state = "no state"
        self.user_settings.github_user = "testing user"
        self.user_settings.save()


    def test_get_targets(self):
        records = list(get_user_settings())

        assert_equal(1, len(records))
        assert_equal(
            records[0].github_user,
            self.user_settings.github_user
        )
        assert_equal(
            records[0].oauth_state,
            self.user_settings.oauth_state
        )
        assert_equal(
            records[0].oauth_access_token,
            self.user_settings.oauth_access_token
        )
        assert_equal(
            records[0].oauth_token_type,
            self.user_settings.oauth_token_type
        )

    @mock.patch('website.addons.github.api.GitHub.user')
    @mock.patch('website.addons.github.api.GitHub')
    def test_do_migration(self, mock_github, mock_github_user):
        mock_github_user.id.return_value = "testing user id"
        do_migration(get_user_settings())
        self.user_settings.reload()
        assert_true(self.user_settings.oauth_settings)
        assert_true(self.user_settings.oauth_state)
        assert_equal(
            self.user_settings.oauth_settings.github_user_name,
            "testing user"
        )
        assert_equal(
            self.user_settings.oauth_settings.oauth_access_token,
            "testing acess token"
        )
        assert_equal(
            self.user_settings.oauth_settings.oauth_token_type,
            "testing token type"
        )
        assert_equal(
            self.user_settings.oauth_settings.github_user_id,
            "testing user id"
        )

if __name__ == '__main__':
    main()
