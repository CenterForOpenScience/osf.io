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
from website.share_window.model import ShareWindow


from scripts import utils as script_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def delete_old_windows(user, dry_run):

    query = Q('_id', 'eq', user._id)
    for node in Node.find(query):
        node.is_public = True


def migrate_user(user, dry_run):


    ShareWindow().create(user)


def get_targets():
    return core.User.find()


def main(dry_run):
    users = get_targets()
    for user in users:
#        delete_old_windows(user, dry_run)
        migrate_user(user, dry_run)


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    dry_run = 'dry' in sys.argv

    # Log to file
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    main(dry_run=dry_run)
