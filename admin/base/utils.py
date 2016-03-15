"""
Utility functions
"""


def osf_admin_check(user):
    """Determines if user is in osf_admin group

    :param user:
    :return:
    """
    return user.is_in_group('osf_admin')
