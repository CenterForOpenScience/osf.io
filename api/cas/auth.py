import json

import jwe
import jwt

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from api.base import settings

from framework.auth import register_unconfirmed
from framework.auth import campaigns
from framework.auth.core import get_user
from framework.auth.exceptions import DuplicateEmailError
from framework.auth.views import send_confirm_email

from website.addons.twofactor.models import TwoFactorUserSettings


class CasAuthentication(BaseAuthentication):

    media_type = 'text/plain'

    def authenticate(self, request):

        payload = decrypt_payload(request.body)
        data = payload.get('data')
        # The `data` payload structure for type "LOGIN"
        # {
        #     "type": "LOGIN",
        #     "user": {
        #         "email": "testuser@fakecos.io",
        #         "password": "f@kePa$$w0rd",
        #         "verificationKey": "ga67ptH4AF4HtMlFxVKP4do7HAaAPC",
        #         "oneTimePassword": "123456",
        #         "remoteAuthenticated": False,
        #     },
        # }
        if data.get('type') == "LOGIN":
            # initial verification:
            user, error_message = handle_login(data.get('user'))
            if user and not error_message:
                # initial verification success, check two-factor
                if not get_user_with_two_factor(user):
                    # two-factor not required, check user status
                    error_message = verify_user_status(user)
                    if error_message:
                        # invalid user status
                        raise AuthenticationFailed(detail=error_message)
                    # valid user status
                    return user, None
                # two-factor required
                error_message = verify_two_factor(user, data.get('user').get('oneTimePassword'))
                if error_message:
                    # two-factor verification failed
                    raise AuthenticationFailed(detail=error_message)
                # two-factor success, check user status
                error_message = verify_user_status(user)
                if error_message:
                    # invalid user status
                    raise AuthenticationFailed(detail=error_message)
                # valid user status
                return user, None
            # initial verification fails
            raise AuthenticationFailed(detail=error_message)
        # The `data` payload structure for type "REGISTER"
        # {
        #     "type": "REGISTER",
        #     "user": {
        #         "fullname": "User Test",
        #         "email": "testuser@fakecos.io",
        #         "password": "f@kePa$$w0rd",
        #         "campaign": None,
        #     },
        # },
        elif data.get('type') == "REGISTER":
            user, error_message = handle_register(data.get('user'))
            if user and not error_message:
                return user, None
            raise AuthenticationFailed(detail=error_message)

        return AuthenticationFailed


def handle_login(user):

    email = user.get('email')
    remote_authenticated = user.get('remoteAuthenticated')
    verification_key = user.get('verificationKey')
    password = user.get('password')
    if not email or not (remote_authenticated or verification_key or password):
        return None, 'MISSING_CREDENTIALS'

    user = get_user(email)
    if not user:
        return None, 'ACCOUNT_NOT_FOUND'

    if remote_authenticated:
        return user, None

    if verification_key:
        if verification_key == user.verification_key:
            return user, None
        return None, 'INVALID_VERIFICATION_KEY'

    if password:
        if user.check_password(password):
            return user, None
        return None, 'INVALID_PASSWORD'


def handle_register(user):

    fullname = user.get('fullname')
    email = user.get('email')
    password = user.get('password')
    if not (fullname and email and password):
        return None, 'MISSING_CREDENTIALS'

    campaign = user.get('campaign')
    if campaign and campaign not in campaigns.CAMPAIGNS:
        campaign = None
    try:
        user = register_unconfirmed(
            email,
            password,
            fullname,
            campaign=campaign,
        )
    except DuplicateEmailError:
        return None, 'ALREADY_REGISTERED'

    send_confirm_email(user, email=user.username)
    return user, None


def decrypt_payload(body):
    if not settings.API_CAS_ENCRYPTION:
        try:
            return json.loads(body)
        except TypeError:
            raise AuthenticationFailed
    try:
        payload = jwt.decode(
            jwe.decrypt(body, settings.JWE_SECRET),
            settings.JWT_SECRET,
            options={'verify_exp': False},
            algorithm='HS256'
        )
    except (jwt.InvalidTokenError, TypeError):
        raise AuthenticationFailed
    return payload


def get_user_with_two_factor(user):
    try:
        return TwoFactorUserSettings.find_one(Q('owner', 'eq', user._id))
    except ModularOdmException:
        return None


def verify_two_factor(user, one_time_password):
    if not one_time_password:
        return 'TWO_FACTOR_AUTHENTICATION_REQUIRED'

    two_factor = get_user_with_two_factor(user)
    if two_factor and two_factor.verify_code(one_time_password):
        return None
    return 'INVALID_ONE_TIME_PASSWORD'


def verify_user_status(user):
    if not user.is_claimed:
        return 'USER_NOT_CLAIMED'
    if user.is_merged:
        return 'USER_MERGED'
    if user.is_disabled:
        return 'USER_DISABLED'
    if not user.is_registered:
        return 'USER_NOT_REGISTERED'
    if not user.is_active:
        return 'USER_NOT_ACTIVE'
    return None
