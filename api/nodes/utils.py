import itertools

from modularodm import Q

from website.util import permissions as osf_permissions
from website.models import Node

def get_visible_nodes_for_user(user, include_public=True):

    query = (
        Q('is_public', 'eq', True) |
        Q('contributors', 'icontains', user._id)
    )

    admin_nodes = Node.find(Q('permissions.{0}'.format(user._id), 'in', [osf_permissions.ADMIN]))
    # flatten list-of-lists of node children
    admin_node_children = list(itertools.chain(*[
        list(node.get_descendants_recursive()) for node in admin_nodes
    ]))
    allowed_nodes = set(
        [node for node in Node.find(query)] + admin_node_children
    )
    return allowed_nodes
