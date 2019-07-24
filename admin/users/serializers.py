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

    potential_spam_profile_content = {
        'schools': user.schools,
        'jobs': user.jobs
    }

    return {
        'username': user.username,
        'name': user.fullname,
        'id': user._id,
        'emails': user.emails.values_list('address', flat=True),
        'last_login': user.date_last_login,
        'confirmed': user.date_confirmed,
        'registered': user.date_registered,
        'deleted': user.deleted,
        'disabled': user.date_disabled if user.is_disabled else False,
        'two_factor': user.has_addon('twofactor'),
        'osf_link': user.absolute_url,
        'system_tags': user.system_tags,
        'is_spammy': user.is_spammy,
        'spam_status': user.spam_status,
        'unclaimed': bool(user.unclaimed_records),
        'requested_deactivation': bool(user.requested_deactivation),
        'osf_groups': [serialize_group_for_user(group, user) for group in user.osf_groups],
        'potential_spam_profile_content': user._get_spam_content(potential_spam_profile_content),
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

def serialize_simple_preprint(preprint):
    return {
        'id': preprint._id,
        'title': preprint.title,
        'number_contributors': len(preprint.contributors),
        'deleted': preprint.is_deleted,
        'public': preprint.verified_publishable,
        'spam_status': preprint.spam_status,
    }
