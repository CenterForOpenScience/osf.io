import json

from rest_framework.exceptions import AuthenticationFailed

import jwe
import jwt

from api.base import settings
from api.base.authentication.drf import check_user
from api.base.exceptions import (UnconfirmedAccountError, UnclaimedAccountError, DeactivatedAccountError,
                                 MergedAccountError, InvalidAccountError)

from addons.twofactor.models import UserSettings as TwoFactorUserSettings

# user status
USER_ACTIVE = 'USER_ACTIVE'
USER_NOT_CLAIMED = 'USER_NOT_CLAIMED'
USER_NOT_CONFIRMED = 'USER_NOT_CONFIRMED'
USER_DISABLED = 'USER_DISABLED'
USER_STATUS_INVALID = 'USER_STATUS_INVALID'

# login and registration exceptions
MISSING_CREDENTIALS = 'MISSING_CREDENTIALS'
ACCOUNT_NOT_FOUND = 'ACCOUNT_NOT_FOUND'
INVALID_PASSWORD = 'INVALID_PASSWORD'
INVALID_VERIFICATION_KEY = 'INVALID_VERIFICATION_KEY'
INVALID_ONE_TIME_PASSWORD = 'INVALID_ONE_TIME_PASSWORD'
TWO_FACTOR_AUTHENTICATION_REQUIRED = 'TWO_FACTOR_AUTHENTICATION_REQUIRED'
ALREADY_REGISTERED = 'ALREADY_REGISTERED'

# oauth
SCOPE_NOT_FOUND = 'SCOPE_NOT_FOUND'
SCOPE_NOT_ACTIVE = 'SCOPE_NOT_ACTIVE'
TOKEN_NOT_FOUND = 'TOKEN_NOT_FOUND'
TOKEN_OWNER_NOT_FOUND = 'TOKEN_OWNER_NOT_FOUND'

# general
INVALID_REQUEST_BODY = 'INVALID REQUEST BODY'
API_NOT_IMPLEMENTED = 'API NOT IMPLEMENTED'


def decrypt_payload(body):
    """
    Decrypt the payload.

    :param body: the JWE/JwT encrypted payload body
    :return: the decrypted json payload
    """

    try:
        payload = jwt.decode(
            jwe.decrypt(body, settings.JWE_SECRET),
            settings.JWT_SECRET,
            options={'verify_exp': False},
            algorithm='HS256'
        )
    except (jwt.InvalidTokenError, TypeError):
        raise AuthenticationFailed(detail=INVALID_REQUEST_BODY)
    return payload


def get_user_status(user):
    """
    Get the status of a given user/account.

    :param user: the user instance
    :return: the user's status in String
    """

    try:
        check_user(user)
        return USER_ACTIVE
    except UnconfirmedAccountError:
        return USER_NOT_CONFIRMED
    except UnclaimedAccountError:
        return USER_NOT_CLAIMED
    except DeactivatedAccountError:
        return USER_DISABLED
    except MergedAccountError or InvalidAccountError:
        return USER_STATUS_INVALID


def verify_two_factor(user, one_time_password):
    """
    Check users' two factor settings after they successful pass the initial verification.

    :param user: the osf user
    :param one_time_password: the one time password
    :return: None, if two factor is not required
             None, if two factor is required and one time password passes verification
             TWO_FACTOR_AUTHENTICATION_REQUIRED, if two factor is required but one time password is not provided
             INVALID_ONE_TIME_PASSWORD if two factor is required but one time password fails verification
    """

    try:
        two_factor = TwoFactorUserSettings.objects.get(owner_id=user.pk)
    except TwoFactorUserSettings.DoesNotExist:
        two_factor = None

    if not two_factor:
        return None

    if not one_time_password:
        return TWO_FACTOR_AUTHENTICATION_REQUIRED

    if two_factor.verify_code(one_time_password):
        return None
    return INVALID_ONE_TIME_PASSWORD
