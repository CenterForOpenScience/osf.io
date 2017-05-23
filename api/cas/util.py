from django.db.models import Q
from django.utils import timezone

from rest_framework.exceptions import ParseError, ValidationError

import jwe
import jwt

from api.base import settings
from api.base.authentication.drf import check_user
from api.base.exceptions import (UnconfirmedAccountError, UnclaimedAccountError, DeactivatedAccountError,
                                 MergedAccountError, InvalidAccountError)
from api.cas import messages

from addons.twofactor.models import UserSettings as TwoFactorUserSettings

from framework.auth.views import send_confirm_email
from framework.auth.core import generate_verification_key

from osf.models import OSFUser

from website.util.time import throttle_period_expired
from website.mails import send_mail, FORGOT_PASSWORD
from website import settings as web_settings


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
    except (TypeError, jwt.exceptions.InvalidTokenError,
            jwt.exceptions.InvalidKeyError, jwe.exceptions.PyJWEException):
        # TODO: inform Sentry, something is wrong with CAS or someone is trying to hack us
        raise ParseError(detail=messages.INVALID_REQUEST)
    return payload


def verify_user_status(user):
    """
    Verify the status of a given user/account.

    :param user: the user instance
    :return: the user's status in String
    """

    try:
        check_user(user)
    except UnconfirmedAccountError:
        return messages.ACCOUNT_NOT_VERIFIED
    except DeactivatedAccountError:
        return messages.ACCOUNT_DISABLED
    except MergedAccountError or UnclaimedAccountError or InvalidAccountError:
        return messages.INVALID_ACCOUNT_STATUS
    return None


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

    # two factor not required
    if not two_factor:
        return None

    # two factor required
    if not one_time_password:
        return messages.TFA_REQUIRED

    # verify two factor
    if two_factor.verify_code(one_time_password):
        return None
    return messages.INVALID_TOTP


def find_account_for_verify_email(data_user):
    """
    Find account by email and verify if the user has a pending email verification. If so, resend the verification email
    if user hasn't recently make the same request.

    :param data_user: the user object in decrypted data payload
    :return: the user if successful, the error message otherwise
    """

    email = data_user.get('email')
    if not email:
        raise ValidationError(detail=messages.INVALID_REQUEST)

    user = OSFUser.objects.filter(Q(username=email) | Q(emails__icontains=email)).first()
    if not user:
        return None, messages.EMAIL_NOT_FOUND

    if not throttle_period_expired(user.email_last_sent, web_settings.SEND_EMAIL_THROTTLE):
        return None, messages.RESEND_VERIFICATION_THROTTLE_ACTIVE

    try:
        send_confirm_email(user, email, renew=True, external_id_provider=None, external_id=None, destination=None)
    except KeyError:
        return None, messages.EMAIL_ALREADY_VERIFIED

    user.email_last_sent = timezone.now()
    user.save()
    return user, None


def find_account_for_reset_password(data_user):
    """
    Find account by email and verify if the user is eligible for reset password. If so, send the verification email
    if user hasn't recently make the same request.

    :param data_user: the user object in decrypted data payload
    :return: the user if successful, the error message otherwise
    """

    email = data_user.get('email')
    if not email:
        raise ValidationError(detail=messages.INVALID_REQUEST)

    user = OSFUser.objects.filter(Q(username=email) | Q(emails__icontains=email)).first()
    if not user:
        return None, messages.EMAIL_NOT_FOUND

    if not throttle_period_expired(user.email_last_sent, web_settings.SEND_EMAIL_THROTTLE):
        return None, messages.RESET_PASSWORD_THROTTLE_ACTIVE

    if not user.is_active:
        return None, messages.RESET_PASSWORD_NOT_ELIGIBLE

    user.verification_key_v2 = generate_verification_key(verification_type='password')
    send_mail(
        to_addr=email,
        mail=FORGOT_PASSWORD,
        user=user,
        verification_code=user.verification_key_v2['token']
    )
    user.email_last_sent = timezone.now()
    user.save()
    return user, None
