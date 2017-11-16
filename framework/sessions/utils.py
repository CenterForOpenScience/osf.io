# -*- coding: utf-8 -*-


def remove_sessions_for_user(user):
    """
    Permanently remove all stored sessions for the user from the DB.

    :param user: User
    :return:
    """
    from osf.models import Session

    if user._id:
        Session.objects.filter(data__auth_user_id=user._id).delete()


def remove_session(session):
    """
    Remove a session from database

    :param session: Session
    :return:
    """
    from osf.models import Session
    Session.remove_one(session)
