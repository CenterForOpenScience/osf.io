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

from scripts import utils as script_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def migrate_user(user, dry_run):

    query = Q('creator', 'eq', user._id)
    query = query & Q('category', 'eq', "share window")

    if Node.find(query).count() > 0:
        return
    else:
        share_window = Node(creator=user)
        share_window.title = "Share Window"
        share_window.category = "share window"

    if not dry_run:
        user.save()
        share_window.save()


def get_targets():
    return core.User.find()


def main(dry_run):
    users = get_targets()
    for user in users:
        migrate_user(user, dry_run)


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    dry_run = 'dry' in sys.argv

    # Log to file
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    main(dry_run=dry_run)
