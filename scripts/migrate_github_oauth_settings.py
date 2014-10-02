#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate nodes with invalid categories."""

import sys

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
    init_app(routes=False)  # Sets the storage backends on all models
    if 'dry' in sys.argv:
        # print list of affected nodes, totals, etc.
        print "===AddonGithubUserSettings==="
        

    else:
        do_migration(get_user_settings())

class TestMigrateNodeCategories(OsfTestCase):

    def test_get_targets(self):
        # ...

    def test_do_migration(self):
        # ...

if __name__ == '__main__':
    main()
