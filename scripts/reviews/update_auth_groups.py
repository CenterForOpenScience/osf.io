#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Update auth groups for all review providers."""
from __future__ import unicode_literals

import sys
import logging
from website.app import setup_django
from scripts import utils as script_utils
from django.db import transaction

setup_django()
from reviews.models import ReviewProviderMixin
from reviews.permissions import GroupHelper


logger = logging.getLogger(__name__)


def create_provider_auth_groups():
    for cls in ReviewProviderMixin.__subclasses__():
        for provider in cls.objects.all():
            logger.info('Updating auth groups for review provider %s', provider)
            GroupHelper(provider).update_provider_auth_groups()


def main(dry=True):
    # Start a transaction that will be rolled back if any exceptions are un
    with transaction.atomic():
        create_provider_auth_groups()
        if dry:
            # When running in dry mode force the transaction to rollback
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)

    # Allow setting the log level just by appending the level to the command
    if '--debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif '--warning' in sys.argv:
        logger.setLevel(logging.WARNING)
    elif '--info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif '--error' in sys.argv:
        logger.setLevel(logging.ERROR)

    # Finally run the migration
    main(dry=dry)
