import itsdangerous
from django.utils.translation import ugettext_lazy as _

from rest_framework import authentication
from rest_framework.authentication import BasicAuthentication
from rest_framework import exceptions

from framework.auth import cas
from framework.sessions.model import Session
from framework.auth.core import User, get_user
from website import settings


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


class OSFBasicAuthentication(BasicAuthentication):

    # override BasicAuthentication
    def authenticate_credentials(self, userid, password):
        """
        Authenticate the userid and password against username and password.
        """
        user = get_user(email=userid, password=password)

        if userid and user is None:
            raise exceptions.AuthenticationFailed(_('Invalid username/password.'))
        elif userid is None and password is None:
            raise exceptions.NotAuthenticated()
        return (user, None)

    def authenticate_header(self, request):
        return ""

class OSFCASAuthentication(authentication.BaseAuthentication):
    """Check whether the user provides a valid OAuth2 bearer token"""

    def authenticate(self, request):
        client = cas.get_client()  # Returns a CAS server client
        auth_header_field = request.META.get("HTTP_AUTHORIZATION", "")  # TODO: "Authorization", or "HTTP_AUTHORIZATION"?
        try:
            auth_token = cas.parse_auth_header(auth_header_field)
        except cas.CasTokenError:
            raise exceptions.AuthenticationFailed('Must provide bearer token in authorization headers')

        # Use the token to get the associated user ID

        try:
            resp = client.profile(auth_token)
        except cas.CasHTTPError:
            raise exceptions.NotAuthenticated('User provided an invalid OAuth2 access token')

        if resp.authenticated is False:
            raise exceptions.NotAuthenticated('CAS server failed to authenticate this token')

        user_id = resp.user
        user = User.load(user_id)
        if user is None:
            raise exceptions.AuthenticationFailed("Could not find the user associated with this token")

        return user, auth_token

    def authenticate_header(self, request):
        return ""
