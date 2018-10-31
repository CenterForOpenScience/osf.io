"""
Serialize user
"""


def serialize_user(user):

    potential_spam_profile_content = {
        'schools': user.schools,
        'jobs': user.jobs
    }

    return {
        'username': user.username,
        'name': user.fullname,
        'id': user._id,
        'nodes': list(map(serialize_simple_node, user.contributor_to)),
        'emails': user.emails.values_list('address', flat=True),
        'last_login': user.date_last_login,
        'confirmed': user.date_confirmed,
        'registered': user.date_registered,
        'disabled': user.date_disabled if user.is_disabled else False,
        'two_factor': user.has_addon('twofactor'),
        'osf_link': user.absolute_url,
        'system_tags': user.system_tags,
        'is_spammy': user.is_spammy,
        'spam_status': user.spam_status,
        'unclaimed': bool(user.unclaimed_records),
        'requested_deactivation': bool(user.requested_deactivation),
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
