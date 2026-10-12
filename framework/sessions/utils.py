from importlib import import_module

from django.conf import settings as django_conf_settings

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


def remove_sessions_for_user(user):
    """Permanently remove all stored sessions for the given user from DB and/or Cache."""
    if not user:
        return
    from osf.models import UserSessionMap
    session_maps = UserSessionMap.objects.filter(user__id=user.id)
    for key in session_maps.values_list('session_key', flat=True):
        session = SessionStore(session_key=key)
        remove_session(session)
    session_maps.delete()


def remove_session(session):
    """Remove a given session from DB and/or Cache."""
    if session:
        session.flush()
