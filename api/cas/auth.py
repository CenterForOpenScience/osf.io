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
        #The JWT `data` payload is expected in the following structures
        # {
        #     "type": "LOGIN",
        #     "user": {
        #         "email": "",
        #         "passwordHash": "",
        #         "verificationKey": "",
        #     },
        # },
        # {
        #     "type": "TWO_FACTOR",
        #     "user": {
        #         "username": "",
        #         "oneTimePassword": "",
        #     },
        # },
        # {
        #     "type": "REGISTER",
        #     "user": {
        #         "fullname": "",
        #         "email": "",
        #         "password": "",
        #         "campaign": "",
        #     },
        # },
        # coming soon for `type == "INSTITUTION" | "EXTERNAL"

        if data.get('type') == "LOGIN":
            user, error_message = handle_login(data.get('user'))
            if user and not error_message:
                return user, None
            raise AuthenticationFailed(detail=error_message)
        elif data.get('type') == "TWO_FACTOR":
            user, error_message = handle_two_factor(data.get('user'))
            if user and not error_message:
                return user, None
            raise AuthenticationFailed(detail=error_message)
        elif data.get('type') == "REGISTER":
            user, error_message = handle_register(data.get('user'))
            if user and not error_message:
                return user, None
            raise AuthenticationFailed(detail=error_message)

        return AuthenticationFailed


def handle_login(user):

    email = user.get('email')
    verification_key = user.get('verificationKey')
    password_hash = user.get('passwordHash')
    if not email or not (verification_key or password_hash):
        return None, 'MISSING_CREDENTIALS'

    user = get_user(email)
    if not user:
        return None, 'ACCOUNT_NOT_FOUND'

    if verification_key:
        if verification_key == user.verification_key:
            return user, None
        return None, 'INVALID_VERIFICATION_KEY'

    if password_hash:
        if password_hash == user.password:
            return user, None
        return None, 'INVALID_PASSWORD'


def handle_two_factor(user):
    username = user.get('username')
    one_time_password = user.get('oneTimePassword')
    if not username or not one_time_password:
        return None, 'MISSING_CREDENTIALS'

    user = get_user(username)
    if not user:
        return None, 'ACCOUNT_NOT_FOUND'

    two_factor = get_user_with_two_factor(user)
    if two_factor and two_factor.verify_code(one_time_password):
        return user, None
    return None, 'INVALID_ONE_TIME_PASSWORD'


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
