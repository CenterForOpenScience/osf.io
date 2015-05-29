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

# class OSFCASAuthentication(authentication.BaseAuthentication):
#     """Check implement authentication based on user + oauth2 token in cookie"""
#     # TODO: Write
#     # TODO: How will we test this?
#
#     def authenticate(self, request):
#         client = cas.get_client()  # Returns a CAS server client
#         #token_val = request.COOKIES.get(settings.COOKIE_NAME)  ## TODO: Verify that this is the field where CAS server tokens reside in cookie when not making request through an OSF session
#         token_val = None ## TODO: Get token from headers, eg "Authorization": 'Bearer {}" line
#
#         # TODO: How do we unambiguously identify that this is a CAS-originating request and not an OSF setting? Will there be a cookie for a third-party, non OSF, possibly non-browser-based tool?
#         if not token_val:
#             return None
#
#         try:
#             response = client.profile(token_val)
#         except cas.CasHTTPError:
#             raise exceptions.NotAuthenticated()  # TODO: Should we prefer AuthenticationFailed?
#
#         user_id = response.user # TODO finish, start looking for ways to test
#         print user_id  # TODO: What will CAS return: user id, user object, or email? FIXME: delete print statement
#         return (user_id, token_val)

