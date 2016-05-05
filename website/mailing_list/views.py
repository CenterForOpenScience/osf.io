# -*- coding: utf-8 -*-
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    must_not_be_registration,
)
from website.util.permissions import ADMIN

from website.mailing_list.utils import log_message


###############################################################################
# View Functions
###############################################################################

@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def get_node_mailing_list(node, auth, **kwargs):
    return format_node_data_recursive([node], auth.user)

@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def enable_mailing_list(node, **kwargs):
    # TODO: queue task
    node.mailing_enabled = True
    node.save()
    return {'message': 'Successfully enabled mailing lists', 'success': True}


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def disable_mailing_list(node, **kwargs):
    # TODO: queue task
    node.mailing_enabled = False
    node.save()

log_message = log_message

def format_node_data_recursive(nodes, user):
    items = []

    for node in nodes:

        can_read = node.has_permission(user, 'read')
        can_read_children = node.has_permission_on_children(user, 'read')

        if not can_read and not can_read_children:
            continue

        children = []
        # List project/node if user has at least 'read' permissions (contributor or admin viewer) or if
        # user is contributor on a component of the project/node

        if can_read_children:
            children.extend(format_node_data_recursive(
                [
                    n
                    for n in node.nodes
                    if n.primary and
                    not (n.is_deleted or n.is_registration)
                ],
                user
            ))

        item = {
            'node': {
                'id': node._id,
                'url': node.url if can_read else '',
                'title': node.title if can_read else 'Private Project',
                'mailing_list': ('enabled' if node.mailing_enabled else 'disabled') if can_read else None
            },
            'children': children,
            'kind': 'folder' if not node.node__parent or not node.parent_node.has_permission(user, 'read') else 'node',
            'nodeType': node.project_or_component,
            'category': node.category,
            'permissions': {
                'view': can_read,
            },
        }

        items.append(item)

    return items
