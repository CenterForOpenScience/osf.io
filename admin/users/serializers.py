"""
Serialize user
"""


def serialize_group_for_user(group, user):
    return {
        'name': group.name,
        'id': group._id,
        'role': user.group_role(group)
    }

def serialize_user(user):
    return {
        'username': user.username,
        'name': user.fullname,
        'id': user._id,
        'nodes': list(map(serialize_simple_node, user.contributor_or_group_member_to)),
        'emails': user.emails.values_list('address', flat=True),
        'last_login': user.date_last_login,
        'confirmed': user.date_confirmed,
        'registered': user.date_registered,
        'disabled': user.date_disabled if user.is_disabled else False,
        'two_factor': user.has_addon('twofactor'),
        'osf_link': user.absolute_url,
        'system_tags': user.system_tags,
        'unclaimed': bool(user.unclaimed_records),
        'requested_deactivation': bool(user.requested_deactivation),
        'osf_groups': [serialize_group_for_user(group, user) for group in user.osf_groups]
    }


def serialize_simple_node(node):
    return {
        'id': node._id,
        'title': node.title,
        'public': node.is_public,
        'number_contributors': len(node.contributors),
        'spam_status': node.spam_status,
        'is_registration': node.is_registration,
        'deleted': node.is_deleted,
    }
