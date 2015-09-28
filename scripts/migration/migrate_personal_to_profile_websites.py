#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate single value personal to profile_websites list."""

import logging

from modularodm import Q
from website import models
from website.app import init_app


logger = logging.getLogger(__name__)


def main():
    init_app(routes=False)
    logger.info("migrating personal to profileWebsites")
    all_users = 0
    migrated_users = 0
    for user in get_users_with_social_field():
        all_users += 1
        logger.info("Migrating User: %s" % repr(user.fullname))
        if not user.social.get('profileWebsites', None):
            user.social['profileWebsites'] = []
            if user.social.get('personal'):
                migrate_personal_to_profile_websites(user)
                migrated_users += 1
        logger.info("%s/'s social dictionary is now %s" % (repr(user.social), repr(user.fullname)))
        user.save()
    logger.info("merged %d users to profileWebsites out of %d total users" % (migrated_users, all_users))


def get_users_with_social_field():
    return models.User.find(
        Q('social', 'ne', {})
    )


def migrate_personal_to_profile_websites(user):
    user.social['profileWebsites'].append(user.social.get('personal'))

if __name__ == '__main__':
    main()
