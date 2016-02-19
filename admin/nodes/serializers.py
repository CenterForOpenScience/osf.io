from website.project.model import User
from website.util.permissions import reduce_permissions

from admin.users.serializers import serialize_simple_node


def serialize_node(node):
    user_list = {key: reduce_permissions(value) for key, value in node.permissions.iteritems()}
    embargo = node.embargo
    if embargo is not None:
        embargo = node.embargo.end_date

    return {
        'id': node._id,
        'title': node.title,
        'public': node.is_public,
        'parent': node.parent_id,
        'root': node.root._id,
        'is_registration': node.is_registration,
        'date_created': node.date_created,
        'contributors': map(serialize_simple_user, user_list.iteritems()),
        'retraction': node.retraction,
        'embargo': embargo,
        'children': map(serialize_simple_node, node.nodes),
    }


def serialize_simple_user(user_info):
    user = User.load(user_info[0])
    return {
        'id': user._id,
        'name': user.fullname,
        'permission': user_info[1]
    }
