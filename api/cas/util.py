import json

from jwe import decrypt
from jwe import exceptions as jwe_exception
from jwt import decode
from jwt import exceptions as jwt_exception

from addons.twofactor.models import UserSettings as TwoFactorUserSettings

from api.base import settings
from api.base import exceptions as api_exceptions
from api.base.authentication.drf import check_user

from framework import sentry
from framework.auth.core import get_user

from osf.models import OSFUser


def load_request_body_data(request):
    """
    Decrypt and decode the request body and return the data in JSON.

    :param request: the CAS request
    :return: the decrypted request body
    :raise: CASJSONWebEncryptionError
    """

    try:
        request.body = decode(
            decrypt(request.body, settings.JWE_SECRET),
            settings.JWT_SECRET,
            options={'verify_exp': False},
            algorithm='HS256'
        )
        return json.loads(request.body.get('data'))
    except (jwt_exception.InvalidTokenError, jwt_exception.InvalidKeyError,
            jwe_exception.PyJWEException, AttributeError, ValueError):
        sentry.log_message('Error: fail to decrypt or decode CAS request.')
        raise api_exceptions.CASJSONWebEncryptionError


def check_user_status(user):
    """
    Helper method that checks if the user is inactive.

    :param user: the user instance
    :return: the user's status in String if inactive
    :raises: UnconfirmedAccountError, UnclaimedAccountError, DeactivatedAccountError,
             MergedAccountError, InvalidAccountError
    """

    check_user(user)


def verify_two_factor_authentication(user, one_time_password):
    """
    Helper method that checks users' two factor authentication settings.

    :param user: the user object
    :param one_time_password: the time-based one time password
    :return: None
    :raises: TwoFactorRequiredError, TwoFactorFailedError
    """

    try:
        two_factor = TwoFactorUserSettings.objects.get(owner_id=user.pk)
    except TwoFactorUserSettings.DoesNotExist:
        return

    # two factor required
    if not one_time_password:
        raise api_exceptions.TwoFactorRequiredError

    # verify two factor
    if not two_factor.verify_code(one_time_password):
        raise api_exceptions.TwoFactorFailedError

    return


def ensure_external_identity_uniqueness(provider, identity, user):
    """
    Helper method that ensures the uniqueness of external identity. Let A be the user that attempts to link or create an
    OSF account. If there is an existing user (denoted as B) with this exact identity as "VERIFIED", remove the pending
    identity from A. If there are any existing users (denoted as Cs) with this identity as "CREATE" or "LINK", remove
    this pending identity from Cs and remove the provider if there is no other identity for it.

    :param provider: the external identity provider
    :param identity: the external identity of the user
    :param user: the user
    :return: None
    :raises: ExternalIdentityAlreadyClaimedError
    """

    users_with_identity = OSFUser.objects.filter(**{
        'external_identity__{}__{}__isnull'.format(provider, identity): False
    })

    for existing_user in users_with_identity:

        if user and user._id == existing_user._id:
            continue

        if existing_user.external_identity[provider][identity] == 'VERIFIED':
            # TODO: CAS follows up with another request to clear the pending identity on this user
            # TODO: Or write a celery worker that clears pending identities that has expired
            raise api_exceptions.ExternalIdentityAlreadyClaimedError

        existing_user.external_identity[provider].pop(identity)
        if existing_user.external_identity[provider] == {}:
            existing_user.external_identity.pop(provider)
        existing_user.save()

    return


def find_user_by_email_or_guid(user_id=None, email=None, username_only=False):
    """
    Helper method that find the OSF user by user's guid, by email or by username only.

    :param user_id: the user's GUID
    :param email: the user's email
    :param username_only: the flag for username only lookup
    :return: the user or None
    """

    if user_id:
        return OSFUser.load(user_id)

    if email:
        if username_only:
            try:
                return OSFUser.objects.filter(username=email).get()
            except OSFUser.DoesNotExist:
                return None
        return get_user(email)

    return None
