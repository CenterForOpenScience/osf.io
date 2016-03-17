#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migration to add a confirmed boolean to User.email_verifications
"""
import sys
import logging
from modularodm import Q

from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction
from framework.auth import User


logger = logging.getLogger(__name__)


def do_migration():
    for user in User.find(Q('email_verifications', 'ne', {})):
        for token in user.email_verifications:
            if 'confirmed' not in token:
                user.email_verifications[token]['confirmed'] = False


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    do_migration()  # Add required data to fields
    if dry:
        raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        main(dry=dry)
