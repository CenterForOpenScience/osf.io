from rest_framework.exceptions import ValidationError

from addons.twofactor.models import UserSettings as TwoFactorUserSettings

from api.cas import messages, errors
from api.cas import util

from framework import sentry
from framework.auth import get_or_create_user
from framework.auth.cas import validate_external_credential

from osf.models import Institution, OSFUser

from website.mails import send_mail
from website.mails import WELCOME_OSF4I

# TODO: raise API exception, use error_code for CAS, keep error_detail


def handle_login_osf(data_user):
    """
    Handle default login through OSF.

    :param data_user: the user object in decrypted data payload
    :return: a verified user or None, an error message or None, the user's status or None
    """

    email = data_user.get('email')
    remote_authenticated = data_user.get('remoteAuthenticated')
    verification_key = data_user.get('verificationKey')
    password = data_user.get('password')
    one_time_password = data_user.get('oneTimePassword')

    # check if credentials are provided
    if not email or not (remote_authenticated or verification_key or password):
        raise ValidationError(detail=messages.INVALID_REQUEST)

    # retrieve the user
    user = util.find_user_by_email_or_guid(None, email, username_only=False)
    if not user:
        raise ValidationError(detail=errors.ACCOUNT_NOT_FOUND)

    # authenticated by remote authentication
    if remote_authenticated:
        verify_two_factor_authentication(user, one_time_password)
        util.check_user(user)
        return user

    # authenticated by verification key
    if verification_key:
        if verification_key == user.verification_key:
            verify_two_factor_authentication(user, one_time_password)
            util.check_user(user)
        raise ValidationError(detail=errors.INVALID_VERIFICATION_KEY)

    # authenticated by password
    if password:
        if user.check_password(password):
            verify_two_factor_authentication(user, one_time_password)
            util.check_user(user)
        raise ValidationError(detail=errors.INVALID_PASSWORD)


def handle_login_institution(provider):
    """
    Handle login through institution identity provider.

    :param provider: the decrypted provider object
    :return: the user
    :raises: ValidationError
    """

    # check required fields
    institution_id = provider.get('id', '')
    institution_user = provider.get('user', '')
    if not (institution_id and institution_user):
        raise ValidationError(detail=messages.INVALID_REQUEST)

    # check institution
    institution = Institution.load(institution_id)
    if not institution:
        raise ValidationError(detail='Invalid institution id specified "{}"'.format(institution_id))

    # check username (email)
    username = institution_user.get('username', '')
    if not username:
        message = 'Institution login failed: username required'
        sentry.log_message(message)
        raise ValidationError(detail=message)

    # check fullname
    fullname = institution_user.get('fullname', '')
    given_name = institution_user.get('givenName', '')
    family_name = institution_user.get('familyName', '')
    if not fullname:
        fullname = '{} {}'.format(given_name, family_name).strip()
    if not fullname:
        message = 'Institution login failed: fullname required for user {} from institution {}'\
            .format(username, institution_id)
        sentry.log_message(message)
        raise ValidationError(detail=message)

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


def handle_login_external(data_user):
    """
    Handle authentication through non-institution external identity provider

    :param data_user: the decrypted user object
    :return: the user with verified external identity
    :raises: PermissionDenied
    """

    # parse external credential
    external_credential = validate_external_credential(data_user.get('externalIdWithProvider'))
    if not external_credential:
        raise ValidationError(detail=errors.INVALID_EXTERNAL_IDENTITY)

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
        raise ValidationError(errors.ACCOUNT_NOT_FOUND)

    # external identity found, return username for CAS to use default login with username and remote principal
    return user


def verify_two_factor_authentication(user, one_time_password):
    """
    Check users' two factor settings after they successful pass the initial verification.

    :param user: the OSF user
    :param one_time_password: the time-based one time password
    :return: None, TWO_FACTOR_AUTHENTICATION_REQUIRED or INVALID_ONE_TIME_PASSWORD
    """

    try:
        two_factor = TwoFactorUserSettings.objects.get(owner_id=user.pk)
    except TwoFactorUserSettings.DoesNotExist:
        return

    # two factor required
    if not one_time_password:
        raise ValidationError(detail=errors.TWO_FACTOR_AUTHENTICATION_REQUIRED)

    # verify two factor
    if not two_factor.verify_code(one_time_password):
        raise ValidationError(detail=errors.INVALID_TIME_BASED_ONE_TIME_PASSWORD)

    return
