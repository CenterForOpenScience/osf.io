from django.db.models import Q
from django.utils import timezone

from rest_framework.exceptions import ParseError, ValidationError, PermissionDenied

import jwe
import jwt

from api.base import settings
from api.base.authentication.drf import check_user
from api.base.exceptions import (UnconfirmedAccountError, UnclaimedAccountError, DeactivatedAccountError,
                                 MergedAccountError, InvalidAccountError)
from api.cas import messages, cas_errors

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


def is_user_inactive(user):
    """
    Check if the user is inactive.

    :param user: the user instance
    :return: the user's status in String if inactive
    """

    try:
        check_user(user)
    except UnconfirmedAccountError:
        return cas_errors.ACCOUNT_NOT_VERIFIED
    except DeactivatedAccountError:
        return cas_errors.ACCOUNT_DISABLED
    except UnclaimedAccountError:
        return cas_errors.ACCOUNT_NOT_CLAIMED
    except (MergedAccountError, InvalidAccountError):
        return cas_errors.INVALID_ACCOUNT_STATUS
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
        return cas_errors.TFA_REQUIRED

    # verify two factor
    if two_factor.verify_code(one_time_password):
        return None
    return cas_errors.INVALID_TOTP


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
        return None, messages.ALREADY_VERIFIED

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


def ensure_external_identity_uniqueness(provider, identity, user):
    """
    Ensure the uniqueness of external identity. User A is the user that tries to link or create an OSF account.
    1. If there is an existing user B with this identity as "VERIFIED", remove the pending identity from the user A.
       Do not raise 400s or 500s because it rolls back transactions. What's the best practice?
    2. If there is any existing user B with this identity as "CREATE" or "LINK", remove this pending identity from the
       user B and remove the provider if there is no other identity for it.
    
    :param provider: the external identity provider
    :param identity: the external identity of the user
    :param user: the user
    :return: 
    """

    users_with_identity = OSFUser.objects.filter(**{
        'external_identity__{}__{}__isnull'.format(provider, identity): False
    })

    for existing_user in users_with_identity:

        if user and user._id == existing_user._id:
            continue

        if existing_user.external_identity[provider][identity] == 'VERIFIED':
            # clear user's pending identity won't work since API rolls back transactions when status >= 400
            # TODO: CAS will do another request to clear the pending identity on this user
            raise PermissionDenied(detail=cas_errors.EXTERNAL_IDENTITY_CLAIMED)

        existing_user.external_identity[provider].pop(identity)
        if existing_user.external_identity[provider] == {}:
            existing_user.external_identity.pop(provider)
        existing_user.save()

    return
