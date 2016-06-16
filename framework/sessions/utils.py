from modularodm import Q

from .model import Session


def remove_sessions_for_user(user):
    """Permanently remove all stored sessions for the user from the DB.

    :param User user:
    """
    Session.remove(Q('data.auth_user_id', 'eq', user._id))


def remove_session(session):
    """
    Remove a session from database
    :param session:
    :return:
    """

    Session.remove(Q('_id', 'eq', session._id))


def check_cors_compatibility(user_agent):
    return 'MSIE 9' in user_agent;
    pass
