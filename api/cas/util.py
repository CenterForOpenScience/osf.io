from rest_framework.exceptions import PermissionDenied

from api.base.authentication.drf import check_user
from api.base.exceptions import (UnconfirmedAccountError, UnclaimedAccountError, DeactivatedAccountError,
                                 MergedAccountError, InvalidAccountError)
from api.cas import errors

from osf.models import OSFUser


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
            raise PermissionDenied(detail=errors.EXTERNAL_IDENTITY_CLAIMED)

        existing_user.external_identity[provider].pop(identity)
        if existing_user.external_identity[provider] == {}:
            existing_user.external_identity.pop(provider)
        existing_user.save()

    return


def find_user_by_email(email, username_only=False):
    """
    Find the OSF user by email or by username only.
    For performance concern, query on username first, and do not combine both queries.
    
    :param email: the email
    :param username_only: the flag for username only lookup
    :return: the user or None
    """

    try:
        user = OSFUser.objects.filter(username=email).get()
    except OSFUser.DoesNotExist:
        user = None

    if not username_only and not user:
        try:
            user = OSFUser.objects.filter(emails__address__contains=email).get()
        except OSFUser.DoesNotExist:
            user = None

    return user
