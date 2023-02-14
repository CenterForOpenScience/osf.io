from datetime import datetime


def remove_sessions_for_user(user):
    """
    Permanently remove all stored sessions for the user from the DB.

    :param user: User
    :return:
    """

    # Note 1: the query is very expensive since the auth_user_id needs to be decoded
    # Note 2: this needs to be async
    # Note 3: it only works for DB backend
    # Note 4: a better solution is to have a separate table map user and their sessions
    # Note 5: an even better solution is to extend Django session and add user id as a field, see
    #         https://docs.djangoproject.com/en/3.2/topics/http/sessions/#extending-database-backed-session-engines
    from django.contrib.sessions.models import Session
    if user._id:
        # find all unexpired sessions
        session_keys = []
        sessions = Session.objects.filter(expire_date__gte=datetime.now())
        # for each, decode and return a queryset of all whose session_data['auth_user_id'] is user_id
        for session in sessions:
            if user._id == session.get_decoded().get('auth_user_id'):
                session_keys.append(session.session_key)
        Session.objects.filter(pk__in=session_keys).delete()


def remove_session(session):
    """
    Remove a session from database

    :param session: Session
    :return:
    """
    session.flush()
