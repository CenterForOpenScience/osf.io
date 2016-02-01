from website.project.model import User
from website.util.permissions import reduce_permissions

from admin.users.serializers import serialize_simple_node


def serialize_node(node):
    user_list = {key: reduce_permissions(value) for key, value in node.permissions.iteritems()}
    return {
        'id': node._id,
        'title': node.title,
        'public': node.is_public,
        'parent': node.parent_id,
        'contributors': map(serialize_simple_user, user_list.iteritems()),
        'children': map(serialize_simple_node, node.nodes),
    }


def serialize_simple_user(user_info):
    user = User.load(user_info[0])
    return {
        'id': user._id,
        'name': user.fullname,
        'permission': user_info[1]
    }
