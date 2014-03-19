from website.models import Node

from website.addons.gitlab.api import client
from website.addons.gitlab.utils import setup_user, setup_node

def migrate_node(node):

    # Quit if no files
    if not node.files_current:
        return

    # Ensure Gitlab project
    node_settings = setup_node(node, initialize=False)
    creator_settings = node.creator.get_addon('gitlab')

    # Hack: Remove contributor from project list; we'll add them back soon
    client.deleteprojectmember(
        node_settings.project_id,
        creator_settings.user_id
    )

    # Ensure Gitlab users
    for contrib in node.contributors:
        if contrib.is_active() and contrib != node.creator:
            setup_user(contrib)
        node_settings.after_add_contributor(node, contrib)


def migrate_nodes():

    for node in Node.find():
        migrate_node(node)


if __name__ == '__main__':
    migrate_nodes()
