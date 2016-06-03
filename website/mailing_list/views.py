# -*- coding: utf-8 -*-
from flask import request

from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    must_not_be_registration,
)
from website.util.permissions import ADMIN, READ
from website.mailing_list import utils


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
    utils.celery_create_list(node._id)
    node.mailing_enabled = True
    node.save()
    return {'message': 'Successfully enabled mailing lists', 'success': True}


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def disable_mailing_list(node, **kwargs):
    utils.celery_delete_list(node._id)
    node.mailing_updated = True
    node.mailing_enabled = False
    node.save()

def flask_unsubscribe_user(*args, **kwargs):
    message = request.form
    unsub = message.get('recipient', None)
    mailing_list = message.get('mailing-list', None)
    utils.unsubscribe_user_hook(unsub, mailing_list)

def flask_log_message(*args, **kwargs):
    message = request.form
    target = message.get('To', None)
    sender_email = message.get('From', None)
    utils.log_message(target, sender_email, message)

def format_node_data_recursive(nodes, user):
    items = []

    for node in nodes:

        can_read = node.has_permission(user, READ)
        can_read_children = node.has_permission_on_children(user, READ)

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
                    n.is_mutable_project
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
