import itsdangerous

from django.middleware.csrf import get_token
from django.utils.translation import ugettext_lazy as _

import waffle
from rest_framework import authentication
from rest_framework.authentication import BasicAuthentication, CSRFCheck
from rest_framework import exceptions

from addons.twofactor.models import UserSettings as TwoFactorUserSettings
from api.base import settings as api_settings
from api.base.exceptions import (
    UnconfirmedAccountError, UnclaimedAccountError, DeactivatedAccountError,
    MergedAccountError, InvalidAccountError, TwoFactorRequiredError,
)
from framework.auth import cas
from framework.auth.core import get_user
from osf import features
from osf.models import OSFUser, Session
from osf.utils.fields import ensure_str
from website import settings


def get_session_from_cookie(cookie_val):
    """
    Given a cookie value, return the `Session` object or `None`.

    :param cookie_val: the cookie
    :return: the `Session` object or None
    """

    try:
        session_id = ensure_str(itsdangerous.Signer(settings.SECRET_KEY).unsign(cookie_val))
    except itsdangerous.BadSignature:
        return None
    try:
        session = Session.objects.get(_id=session_id)
        return session
    except Session.DoesNotExist:
        return None


def check_user(user):
    """
    Check and verify user status.

                                    registered  confirmed   disabled    merged  usable-password
    ACTIVE:                             x           x           o           o           x
    NOT_CONFIRMED (default)     :       o           o           o           o           x
    NOT_CONFIRMED (external)    :       o           o           o           o           o
    NOT_CLAIMED                 :       o           o           o           o           o
    DISABLED                    :       x           x           x           o           x
    USER_MERGED                 :       x           x           o           x           o

    Unlike users created via username-password signup, unconfirmed accounts created by an external
    IdP (e.g. ORCiD Login) have unusable passwords. To detect them, check the ``external_identity``
    property of the user object. See ``created_by_external_idp_and_unconfirmed()`` for details.

    :param user: the user object to check
    :raises `UnconfirmedAccountError` if the user was created via default useraname / password
        sign-up, or if via ORCiD login with pending status "LINK" or "CREATE" to confirm
    :raises `UnclaimedAccountError` if the user was created as an unregistered contributor of a
        project or group waiting to be claimed
    :raises `DeactivatedAccountError` if the user has been disabled / deactivated
    :raises `MergedAccountError` if the user has been merged into another account
    :raises `InvalidAccountError` if the user is not active and not of the expected inactive status
    :returns nothing if user is active and no exception is raised
    """

    # An active user must be registered, claimed, confirmed, not merged, not disabled, and either
    # has a usable password or has a verified external identity.
    if user.is_active:
        return

    # The user has been disabled / deactivated
    if user.is_disabled:
        raise DeactivatedAccountError

    # The user has been merged into another one
    if user.is_merged:
        raise MergedAccountError

    # The user has not been confirmed or claimed
    if not user.is_confirmed and not user.is_registered:
        if user.has_usable_password() or created_by_external_idp_and_unconfirmed(user):
            raise UnconfirmedAccountError
        raise UnclaimedAccountError

    # For all other cases, the user status is invalid. Although such status can't be reached with
    # normal user-facing web application flow, it is still possible as a result of direct database
    # access, coding bugs, database corruption, etc.
    raise InvalidAccountError


def created_by_external_idp_and_unconfirmed(user):
    """Check if the user is created by external IdP and unconfirmed.

    There are only three possible values that indicates the status of a user's external identity:
    'LINK', 'CREATE' and 'VERIFIED'. Only 'CREATE' indicates that the user is newly created by an
    external IdP and is unconfirmed.
    """

    return 'CREATE' in set(sum([list(each.values()) for each in list(user.external_identity.values())], []))


# Three customized DRF authentication classes: basic, session/cookie and access token.
# See http://www.django-rest-framework.org/api-guide/authentication/#custom-authentication


class OSFSessionAuthentication(authentication.BaseAuthentication):
    """
    Custom DRF authentication class for API call with OSF cookie/session.
    """

    def authenticate(self, request):
        """
        If request bears an OSF cookie, retrieve the session and verify the user.

        :param request: the request
        :return: the user
        """
        cookie_val = request.COOKIES.get(settings.COOKIE_NAME)
        if not cookie_val:
            return None
        session = get_session_from_cookie(cookie_val)
        if not session:
            return None
        user_id = session.data.get('auth_user_id')
        user = OSFUser.load(user_id)
        if user:
            if waffle.switch_is_active(features.ENFORCE_CSRF):
                self.enforce_csrf(request)
                # CSRF passed with authenticated user
            check_user(user)
            return user, None
        return None

    def enforce_csrf(self, request):
        """
        Same implementation as django-rest-framework's SessionAuthentication.
        Enforce CSRF validation for session based authentication.
        """
        reason = CSRFCheck().process_view(request, None, (), {})
        if reason:
            # CSRF failed, bail with explicit error message
            raise exceptions.PermissionDenied('CSRF Failed: %s' % reason)

        if not request.COOKIES.get(api_settings.CSRF_COOKIE_NAME):
            # Make sure the CSRF cookie is set for next time
            get_token(request)


class OSFBasicAuthentication(BasicAuthentication):
    """
    Custom DRF authentication class for API call with email, password, and two-factor if necessary.
    """

    def authenticate(self, request):
        """
        Overwrite BasicAuthentication to authenticate by email, password and two-factor code.
        `authenticate_credentials` handles email and password,
        `authenticate_twofactor_credentials` handles two-factor.

        :param request: the request
        :return: a tuple of the user and error messages
        """

        user_auth_tuple = super(OSFBasicAuthentication, self).authenticate(request)
        if user_auth_tuple is not None:
            self.authenticate_twofactor_credentials(user_auth_tuple[0], request)
        return user_auth_tuple

    def authenticate_credentials(self, userid, password, request=None):
        """
        Authenticate the user by userid (email) and password.

        :param userid: the username or email
        :param password: the password
        :return: the User
        :raises: NotAuthenticated
        :raises: AuthenticationFailed
        """

        user = get_user(email=userid, password=password)

        if userid and not user:
            raise exceptions.AuthenticationFailed(_('Invalid username/password.'))
        elif userid is None or not password:
            raise exceptions.NotAuthenticated()

        check_user(user)
        return user, None

    @staticmethod
    def authenticate_twofactor_credentials(user, request):
        """
        Authenticate the user's two-factor one time password code.

        :param user: the user
        :param request: the request
        :raises TwoFactorRequiredError
        :raises AuthenticationFailed
        """

        try:
            two_factor = TwoFactorUserSettings.objects.get(owner_id=user.pk)
        except TwoFactorUserSettings.DoesNotExist:
            two_factor = None
        if two_factor and two_factor.is_confirmed:
            otp = request.META.get('HTTP_X_OSF_OTP')
            if otp is None:
                raise TwoFactorRequiredError()
            if not two_factor.verify_code(otp):
                raise exceptions.AuthenticationFailed(_('Invalid two-factor authentication OTP code.'))

    def authenticate_header(self, request):
        """
        Returns custom value other than "Basic" to prevent BasicAuth dialog prompt when returning 401
        """
        return 'Documentation realm="{}"'.format(self.www_authenticate_realm)


class OSFCASAuthentication(authentication.BaseAuthentication):

    def authenticate(self, request):
        """
        Check whether the request provides a valid OAuth2 bearer token.
        The `user` in `cas_auth_response` is the unique GUID of the user. Please do not use
        the primary key `id` or the email `username`.

        :param request: the request
        :return: the user who owns the bear token and the cas repsonse
        """

        client = cas.get_client()
        try:
            auth_header_field = request.META['HTTP_AUTHORIZATION']
            auth_token = cas.parse_auth_header(auth_header_field)
        except (cas.CasTokenError, KeyError):
            return None

        try:
            cas_auth_response = client.profile(auth_token)
        except cas.CasHTTPError:
            raise exceptions.NotAuthenticated(_('User provided an invalid OAuth2 access token'))

        if cas_auth_response.authenticated is False:
            raise exceptions.NotAuthenticated(_('CAS server failed to authenticate this token'))

        user = OSFUser.load(cas_auth_response.user)
        if not user:
            raise exceptions.AuthenticationFailed(_('Could not find the user associated with this token'))

        check_user(user)
        return user, cas_auth_response

    def authenticate_header(self, request):
        """
        Return an empty string.
        """
        return ''
