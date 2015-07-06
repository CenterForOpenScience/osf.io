# -*- coding: utf-8 -*-
"""Remove conference administrators from COS staff using personal email
addresses and replace with staff email account.
"""

import sys
import logging

from modularodm import Q

from website import models
from website.app import init_app

from scripts import utils as scripts_utils


STAFF_EMAIL = 'presentations@cos.io'
PERSONAL_ACCOUNTS = [
    'andrew@cos.io',
    'sara.d.bowman@gmail.com',
    'KatyCain526@gmail.com',
]

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def migrate_conference(conference, staff_user, personal_accounts, dry_run=True):
    nodes = models.Node.find(
        Q('system_tags', 'eq', conference.endpoint) |
        Q('tags', 'eq', conference.endpoint)
    )
    for node in nodes:
        migrate_node(node, conference, staff_user, personal_accounts, dry_run=dry_run)


def migrate_node(node, conference, staff_user, personal_accounts, dry_run=True):
    for admin in conference.admins:
        if admin.username in personal_accounts and admin in node.contributors:
            logger.info(
                u'Removing admin {0} from node {1}'.format(
                    admin.fullname,
                    node.title,
                )
            )
            if not dry_run:
                node.remove_contributor(admin, log=False, auth=None)
    if staff_user not in node.contributors:
        logger.info(
            u'Adding staff email {0} to node {1}'.format(
                staff_user.fullname,
                node.title,
            )
        )
        if not dry_run:
            node.add_contributor(staff_user, log=False)
    node.save()


def main(dry_run=True):
    init_app(set_backend=True, routes=False)
    staff_user = models.User.find_one(Q('username', 'eq', STAFF_EMAIL))
    for conference in models.Conference.find():
        migrate_conference(conference, staff_user, PERSONAL_ACCOUNTS, dry_run=dry_run)


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)
