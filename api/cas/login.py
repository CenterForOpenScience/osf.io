from api.base import exceptions as api_exceptions
from api.cas.util import check_user_status, verify_two_factor_authentication, find_user_by_email_or_guid

from framework import sentry
from framework.auth import get_or_create_user
from framework.auth.cas import parse_external_credential

from osf.models import Institution, OSFUser

from website.mails import send_mail
from website.mails import WELCOME_OSF4I


def osf_login(user_data):
    """
    Handle default login through OSF.

    :param user_data: the user's credential
    :return: the user if credentials validates
    :raises: MalformedRequestError, AccountNotFoundError, InvalidVerificationKeyError, InvalidPasswordError,
             UnconfirmedAccountError, UnclaimedAccountError, DeactivatedAccountError, MergedAccountError,
             InvalidAccountError, TwoFactorRequiredError, TwoFactorFailedError
    """

    email = user_data.get('email')
    remote_authenticated = user_data.get('remoteAuthenticated')
    verification_key = user_data.get('verificationKey')
    password = user_data.get('password')
    one_time_password = user_data.get('oneTimePassword')

    # check if required credentials are provided
    if not email or not (remote_authenticated or verification_key or password):
        raise api_exceptions.MalformedRequestError

    # retrieve the user
    user = find_user_by_email_or_guid(None, email, username_only=False)
    if not user:
        raise api_exceptions.AccountNotFoundError

    # authenticated by remote authentication
    if remote_authenticated:
        verify_two_factor_authentication(user, one_time_password)
        check_user_status(user)
        return user

    # authenticated by verification key
    if verification_key:
        if verification_key == user.verification_key:
            verify_two_factor_authentication(user, one_time_password)
            check_user_status(user)
            return user
        raise api_exceptions.InvalidVerificationKeyError

    # authenticated by password
    if password:
        if user.check_password(password):
            verify_two_factor_authentication(user, one_time_password)
            check_user_status(user)
            return user
        raise api_exceptions.InvalidPasswordError


def institution_login(provider_data):
    """
    Handle login through institution identity provider.

    :param provider_data: the provider's credential
    :return: the user if credentials validates
    :raises: MalformedRequestError, InvalidInstitutionLoginError
    """

    # check required fields
    institution_id = provider_data.get('id', '')
    institution_user = provider_data.get('user', '')
    if not (institution_id and institution_user):
        raise api_exceptions.MalformedRequestError

    # check institution
    institution = Institution.load(institution_id)
    if not institution:
        detail = 'Invalid institution for institution login: institution={}.'.format(institution_id)
        sentry.log_message(detail)
        raise api_exceptions.InvalidInstitutionLoginError(detail=detail)

    # check username (email)
    username = institution_user.get('username', '')
    if not username:
        detail = 'Username (email) required for institution login: institution={}'.format(institution_id)
        sentry.log_message(detail)
        raise api_exceptions.InvalidInstitutionLoginError(detail=detail)

    # check fullname
    fullname = institution_user.get('fullname', '')
    given_name = institution_user.get('givenName', '')
    family_name = institution_user.get('familyName', '')
    if not fullname:
        fullname = '{} {}'.format(given_name, family_name).strip()
    if not fullname:
        detail = 'Fullname required for institution login: user={}, institution={}'.format(username, institution_id)
        sentry.log_message(detail)
        raise api_exceptions.InvalidInstitutionLoginError(detail=detail)

    middle_names = institution_user.get('middleNames')
    suffix = institution_user.get('suffix')

    # get or create user
    user, created = get_or_create_user(fullname, username, reset_password=False)

    if created:
        # replace the guessed names
        user.given_name = given_name if given_name else user.given_name
        user.family_name = family_name if family_name else user.family_name
        user.middle_names = middle_names if middle_names else user.middle_names
        user.suffix = suffix if suffix else user.suffix
        user.update_date_last_login()
        # save and register user
        user.save()
        user.register(username)
        # send confirmation email
        send_mail(to_addr=user.username, mail=WELCOME_OSF4I, mimetype='html', user=user)

    if not user.is_affiliated_with_institution(institution):
        user.affiliated_institutions.add(institution)
        user.save()

    return user


def external_login(user_data):
    """
    Handle authentication through non-institution external identity provider

    :param user_data: the user's external credential
    :return: the user if credential validates
    :raises: InvalidExternalIdentityError, AccountNotFoundError
    """

    # parse external credential
    external_credential = parse_external_credential(user_data.get('externalIdWithProvider'))
    if not external_credential:
        raise api_exceptions.InvalidExternalIdentityError

    try:
        user = OSFUser.objects.filter(
            external_identity__contains={
                external_credential.get('provider'): {
                    external_credential.get('id'): 'VERIFIED'
                }
            }
        ).get()
    except OSFUser.DoesNotExist:
        # external identity not found, CAS should redirect the users to create or link their OSF account
        raise api_exceptions.AccountNotFoundError

    # external identity found, return username for CAS to use default login with username and remote principal
    return user
