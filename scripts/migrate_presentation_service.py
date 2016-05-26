import sys
import logging

from framework.auth.core import get_user
from framework.transactions.context import TokuTransaction
from website.project.model import Node
from website.app import init_app
from scripts import utils as script_utils


logger = logging.getLogger(__name__)


def do_migration(records, dry=False):
    for user in records:
        logger.info('Deleting user - {}'.format(user._id))
        if not dry:
            with TokuTransaction():
                migrate_project_contributed(user)
                user.is_disabled = True
                user.save()
    logger.info('{}Deleted {} users'.format('[dry]'if dry else '', len(records)))


def migrate_project_contributed(user):
    count = 0
    for node_id in user.contributed:
        node = Node.load(node_id)
        if node._primary_key in user.unclaimed_records:
            del user.unclaimed_records[node._primary_key]

        node.contributors.remove(user._id)

        node.clear_permission(user)
        if user._id in node.visible_contributor_ids:
            node.visible_contributor_ids.remove(user._id)

        node.save()
        count += 1
        logger.info('Removed user - {} as a contributor from project - {}'.format(user._id, node._id))
    logger.info('Removed user - {} as a contributor from {} projects'.format(user._id, count))


def get_targets():
    users = []
    user1 = get_user(email='presentations@cos.io')
    if user1:
        users.append(user1)
    user2 = get_user(email='presentations@osf.io')
    if user2:
        users.append(user2)
    return users


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    do_migration(get_targets(), dry)


if __name__ == '__main__':
    main()
