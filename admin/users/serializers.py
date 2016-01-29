"""
Serialize user
"""


def serialize_user(user):
    return {
        'name': user.fullname,
        'nodes': None,
        'emails': user.emails,
    }
