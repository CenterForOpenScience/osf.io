import json

from rest_framework.exceptions import APIException, ValidationError, AuthenticationFailed, PermissionDenied
from rest_framework.authentication import BaseAuthentication

from django.utils import timezone

from api.cas import util, messages, cas_errors

from framework import sentry
from framework.auth import register_unconfirmed, get_or_create_user
from framework.auth import campaigns
from framework.auth.cas import validate_external_credential
from framework.auth.core import generate_verification_key
from framework.auth.exceptions import DuplicateEmailError, ChangePasswordError, InvalidTokenError, ExpiredTokenError

from framework.auth.views import send_confirm_email

from osf.models import Institution, OSFUser

from website.mails import send_mail, WELCOME, WELCOME_OSF4I, EXTERNAL_LOGIN_LINK_SUCCESS


class CasJweAuthentication(BaseAuthentication):

    def authenticate(self, request):
        """
        Handle CAS JWE/JWT encrypted authentication request.

        1. The POST request payload is encrypted using a secret and a token only known by CAS and OSF.
        
        2. If authentication succeeds, return (user, None); otherwise, return (None, error_message).

        2. There are five types of authentication with respective payload structure:
        
            2.1 Login
                "data": {
                    "type": "LOGIN",
                    "user": {
                        "email": "testuser@example.com",
                        "password": "abCD12#$",
                        "verificationKey": "K3ISQVqZP82BX6QCt1SW2Em4bN2GHC",
                        "oneTimePasscode": "123456",
                        "remoteAuthenticated": "false",
                    },
                },
            
            2.2 Register
                "data": {
                    "type": "REGISTER",
                    "user": {
                        "fullname": "User Test",
                        "email": "testuser@example.com",
                        "password": "abCD12#$",
                        "campaign": "",
                    },
                },
            
            2.3 Institution Authenticate
                "data", {
                    "type": "INSTITUTION_AUTHENTICATE",
                    "provider": {
                        "idp": "https://login.exampleshibuniv.edu/idp/shibboleth",
                        "id": "esu",
                        "user": {
                            "username": "testuser@exampleshibuniv.edu"
                            "fullname": "",
                            "familyName": "Test",
                            "givenName": "User",
                            "suffix": "",
                            "middleNames": "",
                        },
                    },
                },
            
            2.3 Non-institution External Authenticate
                "data", {
                    "type": "NON_INSTITUTION_EXTERNAL_AUTHENTICATE",
                    "user": {
                        "externalIdWithProvider": "ORCiDProfile#0000-0000-0000-0000",
                        "attributes": {
                            "given-names": "User",
                            "family-name": "Test",
                            ...
                        },
                    },
                },
            
            2.5 Reset Password
                "data": {
                    "type": "RESET_PASSWORD",
                    "user": {
                        "username": "testuser@example.com",
                        "password": "ABcd!@34",
                        "verificationCode": "K3ISQVqZP82BX6QCt1SW2Em4bN2GHC",
                    },
                },
            
            2.6 Verify Email (New Account)
                "data": {
                    "type": "VERIFY_EMAIL",
                    "user": {
                        "emailToVerify": "testuser@example.com",
                        "verificationCode": "K3ISQVqZP82BX6QCt1SW2Em4bN2GHC",
                    },
                },

            2.7 Verify Email (ORCiD)
                "data": {
                    "type": "VERIFY_EMAIL_EXTERNAL",
                    "user": {
                        "emailToVerify": "testuser@example.com",
                        "verificationCode": "K3ISQVqZP82BX6QCt1SW2Em4bN2GHC",
                    },
                },


        :param request: the POST request
        :return: (user, None) or (None, error_message)
        """

        payload = request.body
        data = json.loads(payload['data'])
        auth_type = data.get('type')

        # default login
        if auth_type == 'LOGIN':
            user, error_message, user_status_exception = handle_login(data.get('user'))
            if user and not error_message:
                if user_status_exception:
                    # authentication fails due to invalid user status, raise 403
                    raise PermissionDenied(detail=user_status_exception)
                # authentication succeeds
                return user, None
            # authentication fails due to invalid ro incomplete credential, raise 401
            raise AuthenticationFailed(detail=error_message)

        # register
        if auth_type == 'REGISTER':
            return handle_register(data.get('user'))

        # institution login
        if auth_type == 'INSTITUTION_AUTHENTICATE':
            return handle_institution_authenticate(data.get('provider'))

        # non-institution external authentication: login
        if auth_type == 'EXTERNAL_AUTHENTICATE':
            return handle_non_institution_external_authenticate(data.get('user'))

        # non-institution external authentication: create or link OSF account
        if auth_type == 'CREATE_OR_LINK_OSF_ACCOUNT':
            return handle_create_or_link_osf_account(data.get('user'))

        # reset password
        if auth_type == 'RESET_PASSWORD':
            return handle_reset_password(data.get('user'))

        # verify email
        if auth_type == 'VERIFY_EMAIL':
            return handle_verify_email(data.get('user'))

        # verify email external
        if auth_type == 'VERIFY_EMAIL_EXTERNAL':
            return handle_verify_email_external(data.get('user'))

        # TODO: inform Sentry
        # something is wrong with CAS, raise 400
        raise ValidationError(detail=messages.INVALID_REQUEST)


def handle_login(data_user):
    """
    Handle non-institution authentication.
    1. verify that required credentials are provided
        1.1 if fails, return (None, util.MISSING_CREDENTIALS, None)
    2. load the user
        2.1 if fails, return (None, None, util.ACCOUNT_NOT_FOUND, None)
    3. get user status
        3.1 if user is not claimed, it won't pass the initial verification due to the unusable password
            return (None, None, util.USER_NOT_CLAIMED)
    4. initial verification using password, verification key or a flag for remote authentication
        4.1 if initial verification fails, return (None, <the error message>, None)
            note: for security reasons do not reveal user status if initial verification fails
        4.2 if initial verification passes, perform two factor verification,
            return (user, <the error message returned from two factor verification>, <user's status>)

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
        # TODO: inform Sentry
        # something is wrong with CAS, raise 400
        raise ValidationError(detail=messages.INVALID_REQUEST)

    # retrieve the user
    user = util.find_user_by_email(email, username_only=False)
    if not user:
        return None, cas_errors.ACCOUNT_NOT_FOUND, None

    # authenticated by remote authentication
    if remote_authenticated:
        return user, util.verify_two_factor(user, one_time_password), util.is_user_inactive(user)

    # authenticated by verification key
    if verification_key:
        if verification_key == user.verification_key:
            return user, util.verify_two_factor(user, one_time_password), util.is_user_inactive(user)
        return None, cas_errors.INVALID_KEY, None

    # authenticated by password
    if password:
        if user.check_password(password):
            return user, util.verify_two_factor(user, one_time_password), util.is_user_inactive(user)
        return None, cas_errors.INVALID_PASSWORD, None


def handle_register(data_user):
    """
    Handle new user registration.

    :param data_user: the user object in decrypted data payload
    :return: if registration succeeds, return the newly created unconfirmed user with `None` error message
             otherwise, return a `None` user with respective error message
    """

    fullname = data_user.get('fullname')
    email = data_user.get('email')
    password = data_user.get('password')

    # check if all required credentials are provided
    if not (fullname and email and password):
        # TODO: inform Sentry
        # something is wrong with CAS, raise 400
        raise ValidationError(detail=messages.INVALID_REQUEST)

    # check campaign
    campaign = data_user.get('campaign')
    if campaign and campaign not in campaigns.get_campaigns():
        campaign = None

    # create an unconfirmed user
    try:
        user = register_unconfirmed(
            email,
            password,
            fullname,
            campaign=campaign,
        )
    except DuplicateEmailError:
        # user already registered, raise 403
        raise AuthenticationFailed(detail=messages.ALREADY_REGISTERED)

    # send confirmation email
    try:
        send_confirm_email(user, email=user.username)
    except KeyError:
        # TODO: inform Sentry
        # something is wrong with OSF, raise 500
        raise APIException(detail=messages.RESET_PASSWORD_NOT_ELIGIBLE)

    return user, None


def handle_institution_authenticate(provider):
    """
    Handle institution authentication.

    :param provider: the provider object in decrypted data payload
    :return: the user and a `None` error message
    :raises: AuthenticationFailed
    """
    institution = Institution.load(provider['id'])
    if not institution:
        # TODO: inform Sentry
        # something wrong with CAS, raise 400
        raise ValidationError('Invalid institution id specified "{}"'.format(provider['id']))

    username = provider['user'].get('username')
    fullname = provider['user'].get('fullname')
    given_name = provider['user'].get('givenName')
    family_name = provider['user'].get('familyName')
    middle_names = provider['user'].get('middleNames')
    suffix = provider['user'].get('suffix')

    # use given name and family name to build full name if not provided
    if given_name and family_name and not fullname:
        fullname = given_name + ' ' + family_name

    # institution must provide `fullname`, otherwise we fail the authentication and inform sentry
    if not fullname:
        message = 'Institution login failed: fullname required' \
                  ' for user {} from institution {}'.format(username, provider['id'])
        sentry.log_message(message)
        # something wrong with CAS, raise 400
        raise ValidationError(message)

    # `get_or_create_user()` guesses names from fullname
    # replace the guessed ones if the names are provided from the authentication
    user, created = get_or_create_user(fullname, username, reset_password=False)
    if created:
        if given_name:
            user.given_name = given_name
        if family_name:
            user.family_name = family_name
        if middle_names:
            user.middle_names = middle_names
        if suffix:
            user.suffix = suffix
        user.update_date_last_login()

        # save and register user
        user.save()
        user.register(username)

        # send confirmation email
        send_mail(to_addr=user.username, mail=WELCOME_OSF4I, mimetype='html', user=user)

    if not user.is_affiliated_with_institution(institution):
        user.affiliated_institutions.add(institution)
        user.save()

    return user, None


def handle_non_institution_external_authenticate(data_user):
    """ Handle authentication through non-institution external identity provider
    """

    external_credential = validate_external_credential(data_user.get('externalIdWithProvider'))
    if not external_credential:
        raise PermissionDenied(detail=cas_errors.INVALID_EXTERNAL_IDENTITY)

    user = OSFUser.objects.filter(
        external_identity__contains={
            external_credential.get('provider'): {
                external_credential.get('id'): 'VERIFIED'
            }
        }
    ).first()

    if not user:
        raise PermissionDenied(cas_errors.ACCOUNT_NOT_FOUND)
    # no need to handle invalid user status in this view
    # the final step of login is still handled by the login view
    return user, None


def handle_create_or_link_osf_account(data_user):
    """ Handle creating  or linking external identity with OSF
    """

    email = data_user.get('email')
    provider = data_user.get('externalIdProvider')
    identity = data_user.get('externalId')
    campaign = data_user.get('campaign')
    fullname = '{} {}'.format(
        data_user.get('attributes').get('given-names', ''),
        data_user.get('attributes').get('family-name', '')
    ).strip()

    # privacy settings on ORCiD may not release names, use identity instead
    if not fullname:
        fullname = identity
    # raise validation error if CAS fails to make a valid request
    if not email or not fullname or not provider or not identity:
        raise ValidationError(detail=messages.INVALID_REQUEST)
    # campaign is used for new account creation
    if campaign and campaign not in campaigns.get_campaigns():
        campaign = None

    user = util.find_user_by_email(email, username_only=False)
    external_identity = {provider: {identity: None}}
    util.ensure_external_identity_uniqueness(provider, identity, user)

    if user:
        inactive_status = util.is_user_inactive(user)
        if inactive_status:
            # accounts that are not claimed/verified is eligible and considered as new user
            # TODO: should we clear other pending email verifications and unclaimed records? Yes
            # TODO: should we update user's profile? Yes
            if inactive_status == cas_errors.ACCOUNT_NOT_VERIFIED or inactive_status == cas_errors.ACCOUNT_NOT_CLAIMED:
                external_identity[provider][identity] = 'CREATE'
            # accounts that are disabled or of other inactive status is not eligible
            else:
                raise PermissionDenied(detail=messages.EXTERNAL_IDENTITY_NOT_ELIGIBLE)
        else:
            # existing user
            external_identity[provider][identity] = 'LINK'

        if provider in user.external_identity:
            user.external_identity[provider].update(external_identity[provider])
        else:
            user.external_identity.update(external_identity)

        user.add_unconfirmed_email(email, expiration=None, external_identity=external_identity)
        user.save()

        try:
            # renew is not compatible with external account verification, must be set to False
            # TODO: fix renew for external identity
            send_confirm_email(
                user,
                email,
                renew=False,
                external_id_provider=provider,
                external_id=identity
            )
        except KeyError:
            # TODO: something is wrong, inform Sentry
            raise APIException(detail=messages.REQUEST_FAILED)
    else:
        # new user
        external_identity[provider][identity] = 'CREATE'
        user = OSFUser.create_unconfirmed(
            username=email,
            password=None,
            fullname=fullname,
            external_identity=external_identity,
            campaign=campaign
        )
        user.save()

        try:
            # renew is not compatible with external account verification, must be set to False
            # TODO: fix renew for external identity
            send_confirm_email(
                user,
                user.username,
                renew=False,
                external_id_provider=provider,
                external_id=identity
            )
        except KeyError:
            # TODO: something is wrong, inform Sentry
            raise APIException(detail=messages.REQUEST_FAILED)

    return user, external_identity[provider][identity]


def handle_verify_email_external(data_user):

    email = data_user.get('email')
    token = data_user.get('verificationCode')

    if not email or not token:
        # raise validation error if CAS fails to make a valid request
        raise ValidationError(detail=messages.INVALID_REQUEST)
    user = util.find_user_by_email(email, username_only=False)
    if not user:
        # raise validation error if CAS fails to make a valid request
        raise ValidationError(detail=messages.EMAIL_NOT_FOUND)
    if token not in user.email_verifications:
        # token is invalid
        raise PermissionDenied(detail=messages.INVALID_CODE)

    verification = user.email_verifications[token]
    email = verification['email']
    provider = verification['external_identity'].keys()[0]
    identity = verification['external_identity'][provider].keys()[0]

    if provider not in user.external_identity:
        # wrong provider
        raise PermissionDenied(detail=messages.INVALID_CODE)

    external_identity_status = user.external_identity[provider][identity]
    util.ensure_external_identity_uniqueness(provider, identity, user)

    if not user.is_registered:
        # register user and update email
        user.register(email)

    if not user.emails.filter(address=email.lower()):
        # update email
        user.emails.create(address=email.lower())

    user.date_last_logged_in = timezone.now()
    user.external_identity[provider][identity] = 'VERIFIED'
    user.social[provider.lower()] = identity
    del user.email_verifications[token]

    # generate verification key v1 for CAS login
    user.verification_key = generate_verification_key(verification_type=None)

    if external_identity_status == 'CREATE':
        send_mail(to_addr=user.username, mail=WELCOME, mimetype='html', user=user)
        user.last_cas_action = "verify-new-account"
    elif external_identity_status == 'LINK':
        send_mail(user=user, to_addr=user.username, mail=EXTERNAL_LOGIN_LINK_SUCCESS, external_id_provider=provider)
        user.last_cas_action = "verify-existing-account"
    user.save()
    return user, None


def handle_reset_password(data_user):
    """ Handle password reset.
    """

    email = data_user.get('email')
    token = data_user.get('verificationCode')
    password = data_user.get('password')

    # something is wrong with CAS, raise 400
    if not email or not token or not password:
        raise ValidationError(detail=messages.INVALID_REQUEST)

    # retrieve the user
    user = util.find_user_by_email(email, username_only=False)

    # invalid token
    if not user and user.verify_password_token(token):
        raise PermissionDenied(detail=messages.INVALID_CODE)

    # reset password
    try:
        user.set_password(password)
    except ChangePasswordError:
        # something is wrong with OSF, raise 500
        raise APIException(detail=messages.REQUEST_FAILED)

    # clear verification key v2 for password reset
    user.verification_key_v2 = {}

    # generate verification key v1 for CAS login
    user.verification_key = generate_verification_key(verification_type=None)

    # update last_cas_action
    user.last_cas_action = "reset-password"

    user.save()
    return user, None


def handle_verify_email(data_user):
    """ Handle email verification for new account.
    """

    email = data_user.get('email')
    token = data_user.get('verificationCode')

    # something is wrong with CAS, raise 400
    if not email or not token:
        raise ValidationError(detail=messages.INVALID_REQUEST)

    # retrieve the user, the email must be primary
    user = util.find_user_by_email(email, username_only=True)
    if not user or user.date_confirmed:
        # something is wrong with CAS, raise 400
        raise ValidationError(detail=messages.EMAIL_NOT_FOUND)

    # verify the token
    try:
        email = user.get_unconfirmed_email_for_token(token)
    except (InvalidTokenError or ExpiredTokenError):
        # invalid token
        raise PermissionDenied(detail=messages.INVALID_CODE)

    # register user
    user.register(email)

    # send welcome email
    send_mail(to_addr=user.username, mail=WELCOME, mimetype='html', user=user)

    # clear unclaimed_records, email_verifications and verification key v2
    user.email_verifications = {}
    user.unclaimed_records = {}
    user.verification_key_v2 = {}

    # generate verification key v1 for CAS login
    user.verification_key = generate_verification_key(verification_type=None)
    user.last_cas_action = "verify-new-account"

    user.save()
    return user, None
