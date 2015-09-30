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
        if not user.social.get('profileWebsites', None):
            personal = user.social.get('personal', None)
            user.social['profileWebsites'] = [personal] if personal else []
            migrated_users += 1
        logger.info("{}'s social dictionary is now {}".format(user.social, user.fullname))
        user.save()
    logger.info("merged {} users to profileWebsites out of {} total users".format(migrated_users, all_users))


def get_users_with_social_field():
    return models.User.find(
        Q('social', 'ne', {})
    )


if __name__ == '__main__':
    main()
