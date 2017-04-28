import json

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from django.db.models import Q

from api.cas import util

from framework import sentry
from framework.auth import register_unconfirmed, get_or_create_user
from framework.auth import campaigns
from framework.auth.exceptions import DuplicateEmailError
from framework.auth.views import send_confirm_email

from osf.models import Institution, OSFUser

from website.mails import send_mail, WELCOME_OSF4I


class CasAuthentication(BaseAuthentication):

    media_type = 'text/plain'

    def authenticate(self, request):
        """
        Handle CAS authentication request.
        1. The POST request payload is encrypted using a secret only known by CAS and OSF.
        2. There are three types of authentication with respective payload structure and handling:
            1.1 "LOGIN"
                "data": {
                    "type": "LOGIN",
                    "user": {
                        "email": "",
                        "password": "",
                        "verificationKey": "",
                        "oneTimePasscode": "",
                        "remoteAuthenticated": "",
                    },
                }
            1.2 "REGISTER"
                "data": {
                    "type": "REGISTER",
                    "user": {
                        "fullname": "",
                        "email": "",
                        "password": "",
                        "campaign": "",
                    },
                },
            1.3 "INSTITUTION_AUTHENTICATE"
                "data", {
                    "type": "INSTITUTION_AUTHENTICATE"
                    "provider": {
                        "idp": "",
                        "id": "",
                        "user": {
                            "middleNames": "",
                            "familyName": "",
                            "givenName": "",
                            "fullname": "",
                            "suffix": "",
                            "username": ""
                        },
                    },
                }
        3. If authentication succeed, return (user, None); otherwise, return return (None, error_message).

        :param request: the POST request
        :return: (user, None) or (None, error_message)
        """

        # decrypt the payload and load data
        payload = util.decrypt_payload(request.body)
        data = json.loads(payload['data'])

        # login request
        if data.get('type') == 'LOGIN':
            user, error_message, user_status = handle_login(data.get('user'))
            if user and not error_message:
                if user_status != util.USER_ACTIVE:
                    # authentication fails due to invalid user status
                    raise AuthenticationFailed(detail=user_status)
                return user, None
            # authentication fails due to login exceptions
            raise AuthenticationFailed(detail=error_message)

        if data.get('type') == 'REGISTER':
            user, error_message = handle_register(data.get('user'))
            if user and not error_message:
                return user, None
            raise AuthenticationFailed(detail=error_message)

        if data.get('type') == 'INSTITUTION_AUTHENTICATE':
            return handle_institution_authenticate(data.get('provider'))

        return AuthenticationFailed


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
        return None, util.MISSING_CREDENTIALS, None

    # retrieve the user
    user = OSFUser.objects.filter(Q(username=email) | Q(emails__icontains=email)).first()
    if not user:
        return None, util.ACCOUNT_NOT_FOUND, None

    # verify user status
    user_status = util.get_user_status(user)
    if user_status == util.USER_NOT_CLAIMED:
        return user, None, util.USER_NOT_CLAIMED

    # by remote authentication
    if remote_authenticated:
        return user, util.verify_two_factor(user, one_time_password), user_status

    # by verification key
    if verification_key:
        if verification_key == user.verification_key:
            return user, util.verify_two_factor(user, one_time_password), user_status
        return None, util.INVALID_VERIFICATION_KEY, None

    # by password
    if password:
        if user.check_password(password):
            return user, util.verify_two_factor(user, one_time_password), user_status
        return None, util.INVALID_PASSWORD, None


def handle_register(data_user):
    """
    Handle new user registration.

    :param data_user: the user object in decrypted data payload
    :return: if registration suceed, return the newly created unconfirmed user with `None` error message
             otherwise, return a `None` user with respective error message
    """

    fullname = data_user.get('fullname')
    email = data_user.get('email')
    password = data_user.get('password')

    # check if all required credentials are provided
    if not (fullname and email and password):
        return None, util.MISSING_CREDENTIALS

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
        return None, util.ALREADY_REGISTERED

    # send confirmation email
    send_confirm_email(user, email=user.username)

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
        raise AuthenticationFailed('Invalid institution id specified "{}"'.format(provider['id']))

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
        raise AuthenticationFailed(message)

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
        send_mail(
            to_addr=user.username,
            mail=WELCOME_OSF4I,
            mimetype='html',
            user=user
        )

    if not user.is_affiliated_with_institution(institution):
        user.affiliated_institutions.add(institution)
        user.save()

    return user, None
