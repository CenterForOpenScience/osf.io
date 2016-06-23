#!/usr/bin/env python
# encoding: utf-8
"""Migrate Share Windows to existing users

Run dry run: python -m scripts.migrate_share_window dry
Run migration: python -m scripts.migrate_share_window

"""
import sys
import logging

from modularodm import Q

from website.app import init_app
from framework.auth import core
from website.project.model import Node
from modularodm.exceptions import NoResultsFound
from website.project import new_public_files_collection

from scripts import utils as script_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_targets():
    return core.User.find()


def main(dry_run):
    users = get_targets()
    for user in users:
        try:
            Node.find_one(Q('is_public_files_collection', 'eq', True) & Q('contributors', 'eq', user._id))
        except NoResultsFound:
            new_public_files_collection(user)

if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    dry_run = 'dry' in sys.argv

    # Log to file
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    main(dry_run=dry_run)
