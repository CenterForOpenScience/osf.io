from importlib import import_module

from django.conf import settings as django_conf_settings


def remove_sessions_for_user(user):
    """
    Permanently remove all stored sessions for the user from the DB.

    :param user: User
    :return:
    """

    from osf.models import UserSessionMap
    # SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore
    # session_keys = UserSessionMap.objects.filter(user__id=user.id).values_list('session_key', flat=True)
    pass


def remove_session(session):
    """
    Remove a session from database

    :param session: Session
    :return:
    """
    session.flush()
