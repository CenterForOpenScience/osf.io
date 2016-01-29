"""
Serialize user
"""


def serialize_user(user):
    return {
        'name': user.fullname,
        'nodes': map(serialize_simple_node, user.contributor_to),
        'emails': user.emails,
    }


def serialize_simple_node(node):
    return {
        'id': node._id,
        'title': node.title,
    }
