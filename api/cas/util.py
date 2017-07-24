import json

import jwe
import jwt

from rest_framework.exceptions import ParseError, PermissionDenied

from api.base import settings
from api.base.authentication.drf import check_user
from api.base.exceptions import (UnconfirmedAccountError, UnclaimedAccountError, DeactivatedAccountError,
                                 MergedAccountError, InvalidAccountError)
from api.cas import messages, errors

from framework import sentry

from osf.models import OSFUser


def load_request_body_data(request):
    """
    Decrypt and decode the request body and return the data in JSON.

    :param request: the request
    :return: the decrypted body
    :raise: ParseError, Http 400
    """

    try:
        request.body = jwt.decode(
            jwe.decrypt(request.body, settings.JWE_SECRET),
            settings.JWT_SECRET,
            options={'verify_exp': False},
            algorithm='HS256'
        )
        return json.loads(request.body.get('data'))
    except (AttributeError, TypeError, jwt.exceptions.InvalidTokenError,
            jwt.exceptions.InvalidKeyError, jwe.exceptions.PyJWEException):
        sentry.log_message('Error: fail to decrypt or decode CAS request.')
        raise ParseError(detail=messages.INVALID_REQUEST)


def check_user_status(user):
    """
    Check if the user is inactive.

    :param user: the user instance
    :return: the user's status in String if inactive
    """

    check_user(user)


def is_user_inactive(user):
    """
    Check if the user is inactive.

    :param user: the user instance
    :return: the user's status in String if inactive
    """

    try:
        check_user(user)
    except UnconfirmedAccountError:
        return errors.ACCOUNT_NOT_VERIFIED
    except DeactivatedAccountError:
        return errors.ACCOUNT_DISABLED
    except UnclaimedAccountError:
        return errors.ACCOUNT_NOT_CLAIMED
    except (MergedAccountError, InvalidAccountError):
        return errors.ACCOUNT_STATUS_INVALID
    return None


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
    """

    users_with_identity = OSFUser.objects.filter(**{
        'external_identity__{}__{}__isnull'.format(provider, identity): False
    })

    for existing_user in users_with_identity:

        if user and user._id == existing_user._id:
            continue

        if existing_user.external_identity[provider][identity] == 'VERIFIED':
            # clear user's pending identity won't work since API rolls back transactions when status >= 400
            # TODO: CAS will do another request to clear the pending identity on this user?
            raise PermissionDenied(detail=errors.EXTERNAL_IDENTITY_CLAIMED)

        existing_user.external_identity[provider].pop(identity)
        if existing_user.external_identity[provider] == {}:
            existing_user.external_identity.pop(provider)
        existing_user.save()

    return


def find_user_by_email_or_guid(user_id, email, username_only=False):
    """
    Find the OSF user by user's guid, by email or by username only. In the case of email/username, query on username
    first, and do not combine both queries performance concern.

    :param user_id: the user's GUID
    :param email: the user's email
    :param username_only: the flag for username only lookup
    :return: the user or None
    """

    if user_id:
        try:
            user = OSFUser.objects.filter(guids___id=user_id).get()
        except OSFUser.DoesNotExist:
            user = None
    elif email:
        try:
            user = OSFUser.objects.filter(username=email).get()
        except OSFUser.DoesNotExist:
            user = None
        if not username_only and not user:
            try:
                user = OSFUser.objects.filter(emails__address__contains=email).get()
            except OSFUser.DoesNotExist:
                user = None
    else:
        user = None

    return user
