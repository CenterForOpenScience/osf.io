from django.utils import timezone

from rest_framework import exceptions as drf_exceptions

from api.base import exceptions as api_exceptions
from api.cas import util

from framework.auth import exceptions as auth_exceptions
from framework.auth import register_unconfirmed, campaigns
from framework.auth.cas import get_set_password_url
from framework.auth.core import generate_verification_key
from framework.auth.views import send_confirm_email

from osf import exceptions as osf_exceptions
from osf.models import OSFUser

from website import settings as web_settings
from website.mails import send_mail
from website.mails import WELCOME, EXTERNAL_LOGIN_LINK_SUCCESS, FORGOT_PASSWORD
from website.util.time import throttle_period_expired
from website.util.sanitize import strip_html


def create_unregistered_user(credentials):
    """
    Create an new unregistered account through OSF and send confirmation email.

    :param credentials: the user's information
    :return: the newly created but unregistered user
    :raises: MalformedRequestError, EmailAlreadyRegisteredError, PasswordSameAsEmailError
             InvalidOrBlacklistedEmailError, EmailAlreadyConfirmedError, CASRequestFailedError
    """

    # check required fields
    fullname = credentials.get('fullname')
    email = credentials.get('email')
    password = credentials.get('password')
    if not (fullname and email and password):
        raise api_exceptions.MalformedRequestError

    # check and update campaign
    campaign = credentials.get('campaign')
    if campaign and campaign not in campaigns.get_campaigns():
        campaign = None

    fullname = strip_html(fullname)
    try:
        user = register_unconfirmed(email, password, fullname, campaign=campaign)
    except auth_exceptions.DuplicateEmailError:
        # user already exists
        raise api_exceptions.EmailAlreadyRegisteredError
    except auth_exceptions.ChangePasswordError:
        # password is same as email
        raise api_exceptions.PasswordSameAsEmailError
    except osf_exceptions.ValidationError:
        # email is invalid or its domain is blacklisted
        raise api_exceptions.InvalidOrBlacklistedEmailError
    except ValueError:
        # email has already been confirmed to this user
        raise api_exceptions.EmailAlreadyConfirmedError

    try:
        send_confirm_email(user, email=user.username, renew=False, external_id_provider=None, external_id=None)
    except KeyError:
        raise api_exceptions.CASRequestFailedError

    return user


def register_user(credentials):
    """
    Verify and register the new user that was created through OSF.

    :param credentials: the user's information
    :return: the registered user
    :raises: MalformedRequestError, AccountNotFoundError, EmailAlreadyConfirmedError
             InvalidVerificationCodeError, ExpiredVerificationCodeError
    """

    # check required fields
    user_id = credentials.get('userId')
    email = credentials.get('email')
    token = credentials.get('verificationCode')
    if not ((email or user_id) and token):
        raise api_exceptions.MalformedRequestError

    # retrieve the user (the email must be primary)
    user = util.find_user_by_email_or_guid(user_id, email, username_only=True)
    if not user:
        raise api_exceptions.AccountNotFoundError
    if user.date_confirmed:
        raise api_exceptions.EmailAlreadyConfirmedError

    # verify token, register user and send welcome email
    try:
        email = user.get_unconfirmed_email_for_token(token)
    except auth_exceptions.InvalidTokenError:
        # invalid token
        raise api_exceptions.InvalidVerificationCodeError
    except auth_exceptions.ExpiredTokenError:
        # expired token
        raise api_exceptions.ExpiredVerificationCodeError

    user.register(email)
    send_mail(to_addr=user.username, mail=WELCOME, mimetype='html', user=user)

    # TODO: as discussed with @Steve in person, the following clean up code should be moved into the `.register()`
    # clear email verifications for pending emails (new account, new email, account merge, etc.)
    user.email_verifications = {}
    # clear unclaimed records for unregistered contributors or pending self-claim
    user.unclaimed_records = {}
    # clear verification key v2 for pending password reset
    user.verification_key_v2 = {}

    # generate verification key v1 for automatic CAS login
    user.verification_key = generate_verification_key(verification_type=None)
    user.save()

    return user


def resend_confirmation(credential):

    """
    Find OSF account by email. Verify that the user is eligible for resend new account verification. Resend the
    email if the user hasn't recently make the same request.

    :param credential: the user's information
    :return: the user
    :raises: MalformedRequestError, AccountNotFoundError, Throttled
             CASRequestFailedError, AccountNotEligibleError, EmailAlreadyConfirmedError
    """

    # check required fields
    email = credential.get('email')
    if not email:
        raise api_exceptions.MalformedRequestError

    # retrieve the user
    user = util.find_user_by_email_or_guid(None, email, username_only=False)
    if not user:
        raise api_exceptions.AccountNotFoundError

    try:
        util.check_user_status(user)
    # user must have unconfirmed status
    except api_exceptions.UnconfirmedAccountError:
        # check email throttle
        if not throttle_period_expired(user.email_last_sent, web_settings.SEND_EMAIL_THROTTLE):
            raise api_exceptions.Throttled
        # resend email
        try:
            send_confirm_email(user, email, renew=True, external_id_provider=None, external_id=None)
        except KeyError:
            raise api_exceptions.CASRequestFailedError
        user.email_last_sent = timezone.now()
        user.save()
        return user
    # account with other inactive status are not eligible
    except drf_exceptions.APIException:
        raise api_exceptions.AccountNotEligibleError

    # cannot confirm an active user
    raise api_exceptions.EmailAlreadyConfirmedError


def create_or_link_external_user(credentials):
    """
    Create an unregistered account or link (pending) an existing account to an external identity.

    :param credentials: the user's information
    :return: the newly created unregistered user or the target existing user for link
             both have pending status for external identity to be verified
    :raises: MalformedRequestError, AccountNotEligibleError, CASRequestFailedError
             ExternalIdentityAlreadyClaimedError
    """

    # check required fields
    email = credentials.get('email')
    provider = credentials.get('externalIdProvider')
    identity = credentials.get('externalId')
    fullname = '{} {}'.format(
        credentials.get('attributes').get('given-names', ''),
        credentials.get('attributes').get('family-name', '')
    ).strip()
    if not fullname:
        fullname = identity  # ORCiD's privacy settings may prevent names from being released, use identity instead
    if not (email and fullname and provider and identity):
        raise api_exceptions.MalformedRequestError

    # check and update campaign
    campaign = credentials.get('campaign')
    if campaign and campaign not in campaigns.get_campaigns():
        campaign = None

    # try to retrieve user
    user = util.find_user_by_email_or_guid(None, email, username_only=False)
    external_identity = {
        provider: {
            identity: None
        }
    }
    util.ensure_external_identity_uniqueness(provider, identity, user)

    if user:
        try:
            # check user status
            util.check_user_status(user)
        except api_exceptions.UnconfirmedAccountError or api_exceptions.UnclaimedAccountError:
            # user not confirmed or claimed but in database, create instead of link
            user.fullname = fullname
            user.update_guessed_names()
            user.email_verifications = {}
            user.unclaimed_records = {}
            user.verification_key = {}
            external_identity[provider][identity] = 'CREATE'
        except drf_exceptions.APIException:
            # account with other inactive status are not eligible
            raise api_exceptions.AccountNotEligibleError
        else:
            # existing user, link
            external_identity[provider][identity] = 'LINK'

        # add or update external identity
        if provider in user.external_identity:
            user.external_identity[provider].update(external_identity[provider])
        else:
            user.external_identity.update(external_identity)
        user.add_unconfirmed_email(email, expiration=None, external_identity=external_identity)
        user.save()
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
        # TODO: renew is not compatible for external identity, must be set to `False`, fix this?
        send_confirm_email(
            user,
            email,
            renew=False,
            external_id_provider=provider,
            external_id=identity
        )
    except KeyError:
        raise api_exceptions.CASRequestFailedError

    return user, external_identity[provider][identity]


def register_external_user(credentials):
    """
    Verify and register (link) new (existing) users and update external identity.

    :param credentials: the user's information
    :return: the user and whether created or linked
    :raises: MalformedRequestError, AccountNotFoundError, InvalidVerificationCodeError
             CASRequestFailedError, ExternalIdentityAlreadyClaimedError
    """

    # check required fields
    email = credentials.get('email')
    token = credentials.get('verificationCode')
    if not email or not token:
        raise api_exceptions.MalformedRequestError

    # retrieve the user
    user = util.find_user_by_email_or_guid(None, email, username_only=False)
    if not user:
        raise api_exceptions.AccountNotFoundError

    # check the token and its verification
    if token not in user.email_verifications:
        raise api_exceptions.InvalidVerificationCodeError
    verification = user.email_verifications[token]
    email = verification['email']
    provider = verification['external_identity'].keys()[0]
    identity = verification['external_identity'][provider].keys()[0]
    if provider not in user.external_identity:
        raise api_exceptions.CASRequestFailedError

    created_or_linked = user.external_identity[provider][identity]
    util.ensure_external_identity_uniqueness(provider, identity, user)

    # register/update user, set identity status to verified, clear pending verifications and send emails
    if not user.is_registered:
        user.register(email)
    if not user.emails.filter(address=email.lower()):
        user.emails.create(address=email.lower())
    user.date_last_logged_in = timezone.now()
    user.external_identity[provider][identity] = 'VERIFIED'
    user.social[provider.lower()] = identity
    del user.email_verifications[token]
    if created_or_linked == 'CREATE':
        send_mail(to_addr=user.username, mail=WELCOME, mimetype='html', user=user)
    elif created_or_linked == 'LINK':
        send_mail(to_addr=user.username, mail=EXTERNAL_LOGIN_LINK_SUCCESS, user=user, external_id_provider=provider)

    # generate verification key v1 for automatic CAS login
    user.verification_key = generate_verification_key(verification_type=None)
    user.save()

    return user, created_or_linked


def send_password_reset_email(credential):
    """
    Find account by email and verify if the user is eligible for reset password. If so, send the verification email
    if user hasn't recently make the same request.

    :param credential: the user's information
    :return: the user with pending password reset verification
    :raises: MalformedRequestError, AccountNotFoundError, Throttled
             AccountNotEligibleError
    """

    # check required fields
    email = credential.get('email')
    if not email:
        raise api_exceptions.MalformedRequestError

    # retrieve the user
    user = util.find_user_by_email_or_guid(None, email, username_only=False)
    if not user:
        raise api_exceptions.AccountNotFoundError

    # check throttle
    if not throttle_period_expired(user.email_last_sent, web_settings.SEND_EMAIL_THROTTLE):
        raise api_exceptions.EmailThrottleActiveError

    # check user status
    try:
        util.check_user_status(user)
    except drf_exceptions.APIException:
        raise api_exceptions.AccountNotEligibleError

    # generate verification key v2 for reset password and send email
    user.verification_key_v2 = generate_verification_key(verification_type='password')
    token = user.verification_key_v2.get('token')
    set_password_url = get_set_password_url(user._id, meetings=False)
    send_mail(
        to_addr=email,
        mail=FORGOT_PASSWORD,
        user=user,
        verification_code=token,
        reset_password_url=set_password_url
    )
    user.email_last_sent = timezone.now()
    user.save()

    return user, None


def reset_password(credentials):
    """
    Verify and Reset password for eligible OSF account.

    :param credentials: the user's information
    :return: the user
    :raises: MalformedRequestError, AccountNotFoundError,
             InvalidVerificationCodeError, PasswordSameAsEmailError
    """

    # check required fields
    user_id = credentials.get('userId')
    email = credentials.get('email')
    token = credentials.get('verificationCode')
    password = credentials.get('password')
    if not ((email or user_id) and token and password):
        raise api_exceptions.MalformedRequestError

    # retrieve the user
    user = util.find_user_by_email_or_guid(user_id, email, username_only=False)
    if not user:
        raise api_exceptions.AccountNotFoundError

    # check to token
    if not user.verify_password_token(token):
        raise api_exceptions.InvalidVerificationCodeError

    # reset password
    try:
        user.set_password(password)
    except auth_exceptions.ChangePasswordError:
        raise api_exceptions.PasswordSameAsEmailError

    # clear verification key v2 for password reset
    user.verification_key_v2 = {}

    # generate verification key v1 for automatic CAS login
    user.verification_key = generate_verification_key(verification_type=None)
    user.save()

    return user
