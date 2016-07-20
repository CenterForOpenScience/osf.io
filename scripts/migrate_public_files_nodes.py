#!/usr/bin/env python
# encoding: utf-8
"""Migrate Share Windows to existing users

Run dry run: python -m scripts.migrate_public_files_nodes --dry
Run migration: python -m scripts.migrate_public_files_nodes

"""
import sys
import logging

from website.app import init_app
from framework.auth import core
from website.public_files import give_user_public_files_node
from framework.transactions.context import TokuTransaction

from scripts import utils as script_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main(dry_run):
    users = core.User.find()

    with TokuTransaction():
        for user in users:
            if user.is_registered and user.public_files_node is None:
                give_user_public_files_node(user)

        if dry_run:
            raise BaseException

if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    dry_run = '--dry' in sys.argv

    # Log to file
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    main(dry_run=dry_run)
