"""
Serialize user
"""
# from admin.nodes.serializers import serialize_simple_user


def serialize_user(user):
    two_factor = user.get_addon('twofactor')
    if two_factor is None or two_factor is False:
        two_factor = False
    else:
        two_factor = True
    return {
        'name': user.fullname,
        'id': user._id,
        'nodes': map(serialize_simple_node, user.contributor_to),
        'emails': user.emails,
        'last_login': user.date_last_login,
        'two_factor': two_factor,
    }


def serialize_simple_node(node):
    return {
        'id': node._id,
        'title': node.title,
        'public': node.is_public,
        'number_contributors': len(node.contributors),
    }
