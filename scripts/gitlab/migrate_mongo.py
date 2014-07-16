"""
Create GitLab users and projects.
"""

import re
import logging
from modularodm import Q, signals

from framework.mongo import StoredObject

from website.models import User, Node
from website.app import init_app
from website.project import model as project_model

from website.addons.gitlab.api import client
from website.addons.gitlab.utils import setup_user, setup_node

app = init_app('website.settings', set_backends=True, routes=True)
app.test_request_context().push()

# Disconnect `Node` validators to avoid crashes due to invalid data
signals.before_save.disconnect(project_model.validate_permissions)
signals.before_save.disconnect(project_model.validate_visible_contributors)

email_regex = re.compile(r'^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', re.I)


def migrate_node(node):

    logging.warn('Migrating node {0}'.format(node._id))

    # Quit if no creator
    if not node.contributors or not node.contributors[0] or not node.creator:
        return

    if not node.contributors[0].username:
        return

    # Ensure GitLab add-on added to node
    node.get_or_add_addon('gitlab', log=False)

    # Quit if no files
    if not node.files_current:
        return

    owner = node.contributors[0]

    # Check for duplicate email addresses
    email_duplicates = User.find(Q('username', 'eq', owner.username))
    if email_duplicates.count() > 1:
        logging.error('Duplicate email address: {0}'.format(owner.username))
        return

    # Ensure Gitlab project
    user_settings = setup_user(node.contributors[0])
    node_settings = setup_node(node, check_ready=False)

    if node_settings._migration_done:
        logging.warn('Migration already complete.')
        return

    # Hack: Remove contributor from project list; we'll add them back soon
    client.deleteprojectmember(
        node_settings.project_id,
        user_settings.user_id
    )

    # Ensure Gitlab users
    for contrib in node.contributors:
        if not contrib or not contrib.username:
            continue
        if not email_regex.search(contrib.username):
            continue
        if contrib.is_active() and contrib != node.contributors[0]:
            setup_user(contrib)
        node_settings.after_add_contributor(node, contrib)

    node_settings._migration_done = True
    node_settings.save()

    # Prevent cache from exploding
    StoredObject._clear_caches()


def migrate_nodes():
    """Migrate all nodes."""
    for node in Node.find():
        migrate_node(node)


if __name__ == '__main__':
    migrate_nodes()

