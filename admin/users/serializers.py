"""
Serialize user
"""


def serialize_user(user):
    return {
        'name': user.fullname,
        'id': user._id,
        'nodes': map(serialize_simple_node, user.contributor_to),
        'emails': user.emails,
        'last_login': user.date_last_login,
        'disabled': user.date_disabled if user.is_disabled else False,
        'two_factor': user.has_addon('twofactor'),
    }


def serialize_simple_node(node):
    return {
        'id': node._id,
        'title': node.title,
        'public': node.is_public,
        'number_contributors': len(node.contributors),
        'is_registration': node.is_registration,
        'deleted': node.is_deleted,
    }
