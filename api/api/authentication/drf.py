from rest_framework import authentication
import itsdangerous
from website import settings
from framework.sessions.model import Session
from framework.auth.core import User

def get_session_from_cookie(cookie_val):
    """Given a cookie value, return the `Session` object or `None`."""
    session_id = itsdangerous.Signer(settings.SECRET_KEY).unsign(cookie_val)
    return Session.load(session_id)

# http://www.django-rest-framework.org/api-guide/authentication/#custom-authentication
class OSFSessionAuthentication(authentication.BaseAuthentication):
    """Custom DRF authentication class which works with the OSF's Session object.
    """

    def authenticate(self, request):
        cookie_val = request.COOKIES.get(settings.COOKIE_NAME)
        if not cookie_val:
            return None
        session = get_session_from_cookie(cookie_val)
        if not session:
            return None
        user_id = session.data.get('auth_user_id')
        user = User.load(user_id)
        if user:
            return user, None
        return None
