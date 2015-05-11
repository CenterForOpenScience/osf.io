#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate nodes with invalid categories."""

import logging
import sys

from modularodm import Q
from nose.tools import *

from website import models
from website.app import init_app
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)


#def main(dry=True):
#    init_app(set_backends=True, routes=False, mfr=False)  # Sets the storage backends on all models
#    do_migration(get_targets(), dry=dry)

    
def main():
    # Set up storage backends
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    logger.info("migrating personal to profileWebsites")
            
    for user in get_users_with_personal_websites():
        logger.info(repr(user))
        logger.info(repr(user.social))
        if not user.social.get('profileWebsites'):
            user.social['profileWebsites'] = []
            if user.social.get('personal'):
                migrate_personal_to_profile_websites(user)
        logger.info(repr(user.social))
        if not dry_run:
            user.save()


def get_users_with_personal_websites():
    return models.User.find(
        Q('social', 'ne', None)
    )


def migrate_personal_to_profile_websites(user):
    user.social['profileWebsites'][0] = user.social.get('personal')

if __name__ == '__main__':
    main()
