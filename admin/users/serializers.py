"""
Serialize user
"""
# from admin.nodes.serializers import serialize_simple_user


def serialize_user(user):
    return {
        'name': user.fullname,
        'nodes': map(serialize_simple_node, user.contributor_to),
        'emails': user.emails,
        'last_login': user.date_last_login,
    }


def serialize_simple_node(node):
    return {
        'id': node._id,
        'title': node.title,
        'public': node.is_public,
        'number_contributors': len(node.contributors),
    }
