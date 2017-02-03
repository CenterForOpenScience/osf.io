import json

import jwe
import jwt

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from django.contrib.auth import hashers
from django.db.models import Q
from django.utils import timezone

from addons.twofactor.models import UserSettings

from api.base import settings

from framework.auth import register_unconfirmed, get_or_create_user
from framework.auth import campaigns
from framework.auth.exceptions import DuplicateEmailError
from framework.auth.views import send_confirm_email

from osf.models import Institution, OSFUser

from website.mails import send_mail, WELCOME_OSF4I

UNUSABLE_PASSWORD_PREFIX = hashers.UNUSABLE_PASSWORD_PREFIX

# user status
USER_ACTIVE = 'USER_ACTIVE'
USER_NOT_CLAIMED = 'USER_NOT_CLAIMED'
USER_NOT_CONFIRMED = 'USER_NOT_CONFIRMED'
USER_DISABLED = 'USER_DISABLED'
USER_STATUS_INVALID = 'USER_STATUS_INVALID'

# login exception
MISSING_CREDENTIALS = 'MISSING_CREDENTIALS'
ACCOUNT_NOT_FOUND = 'ACCOUNT_NOT_FOUND'
INVALID_PASSWORD = 'INVALID_PASSWORD'
INVALID_VERIFICATION_KEY = 'INVALID_VERIFICATION_KEY'
INVALID_ONE_TIME_PASSWORD = 'INVALID_ONE_TIME_PASSWORD'
TWO_FACTOR_AUTHENTICATION_REQUIRED = 'TWO_FACTOR_AUTHENTICATION_REQUIRED'

# register exception
ALREADY_REGISTERED = 'ALREADY_REGISTERED'


class CasAuthentication(BaseAuthentication):

    media_type = 'text/plain'

    def authenticate(self, request):

        payload = decrypt_payload(request.body)
        data = json.loads(payload['data'])
        # The `data` payload structure for type "LOGIN"
        # {
        #     "type": "LOGIN",
        #     "user": {
        #         "email": "testuser@fakecos.io",
        #         "password": "f@kePa$$w0rd",
        #         "verificationKey": "ga67ptH4AF4HtMlFxVKP4do7HAaAPC",
        #         "oneTimePassword": "123456",
        #         "remoteAuthenticated": False,
        #     },
        # }
        if data.get('type') == 'LOGIN':
            # initial verification:
            user, error_message = handle_login(data.get('user'))
            if user and not error_message:
                # initial verification success, check two-factor
                if not get_user_with_two_factor(user):
                    # two-factor not required, check user status
                    error_message = verify_user_status(user)
                    if error_message != USER_ACTIVE:
                        # invalid user status
                        raise AuthenticationFailed(detail=error_message)
                    # valid user status
                    return user, None
                # two-factor required
                error_message = verify_two_factor(user, data.get('user').get('oneTimePassword'))
                if error_message:
                    # two-factor verification failed
                    raise AuthenticationFailed(detail=error_message)
                # two-factor success, check user status
                error_message = verify_user_status(user)
                if error_message != USER_ACTIVE:
                    # invalid user status
                    raise AuthenticationFailed(detail=error_message)
                # valid user status
                return user, None
            # initial verification fails
            raise AuthenticationFailed(detail=error_message)

        # The `data` payload structure for type "REGISTER"
        # {
        #     "type": "REGISTER",
        #     "user": {
        #         "fullname": "User Test",
        #         "email": "testuser@fakecos.io",
        #         "password": "f@kePa$$w0rd",
        #         "campaign": None,
        #     },
        # },
        if data.get('type') == 'REGISTER':
            user, error_message = handle_register(data.get('user'))
            if user and not error_message:
                return user, None
            raise AuthenticationFailed(detail=error_message)

        # The `data` payload structure for type "INSTITUTION_AUTHENTICATE":
        # {
        #     "type": "INSTITUTION_AUTHENTICATE"
        #     "provider": {
        #         "idp": "",
        #         "id": "",
        #         "user": {
        #             "middleNames": "",
        #             "familyName": "",
        #             "givenName": "",
        #             "fullname": "",
        #             "suffix": "",
        #             "username": ""
        #     }
        # }
        if data.get('type') == 'INSTITUTION_AUTHENTICATE':
            return handle_institution_authenticate(data.get('provider'))

        return AuthenticationFailed


def handle_institution_authenticate(provider):
    institution = Institution.load(provider['id'])
    if not institution:
        raise AuthenticationFailed('Invalid institution id specified "{}"'.format(provider['id']))

    username = provider['user']['username']
    fullname = provider['user']['fullname']
    given_name = provider['user'].get('givenName')
    family_name = provider['user'].get('familyName')

    # use given name an family name to build full name if not provided
    if given_name and family_name and not fullname:
        fullname = given_name + ' ' + family_name

    # use username if no names are provided
    if not fullname:
        fullname = username

    user, created = get_or_create_user(fullname, username, reset_password=False)

    if created:
        if given_name:
            user.given_name = given_name
        if family_name:
            user.family_name = family_name
        user.middle_names = provider['user'].get('middleNames')
        user.suffix = provider['user'].get('suffix')
        user.date_last_login = timezone.now()
        user.save()

        # User must be saved in order to have a valid _id
        user.register(username)
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


def handle_login(user):

    email = user.get('email')
    remote_authenticated = user.get('remoteAuthenticated')
    verification_key = user.get('verificationKey')
    password = user.get('password')

    # check if credentials are provided
    if not email or not (remote_authenticated or verification_key or password):
        return None, MISSING_CREDENTIALS

    # retrieve the user
    user = OSFUser.objects.filter(Q(username=email) | Q(emails__icontains=email)).first()
    if not user:
        return None, ACCOUNT_NOT_FOUND

    # verify user status
    if verify_user_status(user) == USER_NOT_CLAIMED:
        return None, USER_NOT_CLAIMED

    # by remote authentication
    if remote_authenticated:
        return user, None

    # by verification key
    if verification_key:
        if verification_key == user.verification_key:
            return user, None
        return None, INVALID_VERIFICATION_KEY

    # by password
    if password:
        if user.check_password(password):
            return user, None
        return None, INVALID_PASSWORD


def handle_register(user):

    fullname = user.get('fullname')
    email = user.get('email')
    password = user.get('password')
    if not (fullname and email and password):
        return None, 'MISSING_CREDENTIALS'

    campaign = user.get('campaign')
    if campaign and campaign not in campaigns.get_campaigns():
        campaign = None
    try:
        user = register_unconfirmed(
            email,
            password,
            fullname,
            campaign=campaign,
        )
    except DuplicateEmailError:
        return None, 'ALREADY_REGISTERED'

    send_confirm_email(user, email=user.username)
    return user, None


def get_user_with_two_factor(user):
    return UserSettings.objects.filter(owner_id=user.pk).first()


def verify_two_factor(user, one_time_password):
    if not one_time_password:
        return TWO_FACTOR_AUTHENTICATION_REQUIRED

    two_factor = get_user_with_two_factor(user)
    if two_factor and two_factor.verify_code(one_time_password):
        return None
    return INVALID_ONE_TIME_PASSWORD


def verify_user_status(user):
    """
    Verify users' status.

    Possible User Status during authentication:

                        registered      confirmed       disabled        merged      usable password     claimed
    USER_ACTIVE:        x               x               o               o           x                   ?
    USER_NOT_CONFIRMED: o               o               o               o           x                   ?
    USER_NOT_CLAIMED:   o               o               o               o           o                   ?
    USER_DISABLE:       o               ?               x               o           ?                   ?

    Unreachable User Status (or something is horribly wrong)
    USER_STATUS_INVALID
        USER_MERGED:    ?               ?               ?               x           o                   ?
        !USER_ACTIVE, but does not fall into any of the above category

    :param user: the user
    :return: USER_ACTIVE, USER_NOT_CLAIMED, USER_NOT_CONFIRMED, USER_DISABLED, USER_STATUS_INVALID
    """
    if user.is_active:
        return USER_ACTIVE

    if not user.is_claimed and not user.is_registered and not user.is_confirmed:
        if user.password is None or user.password.startswith(UNUSABLE_PASSWORD_PREFIX):
            return USER_NOT_CLAIMED
        if user.has_usable_password():
            return USER_NOT_CONFIRMED

    if user.is_disabled and not user.is_registered and user.is_claimed:
        return USER_DISABLED

    return USER_STATUS_INVALID


def decrypt_payload(body):
    if not settings.API_CAS_ENCRYPTION:
        try:
            return json.loads(body)
        except TypeError:
            raise AuthenticationFailed
    try:
        payload = jwt.decode(
            jwe.decrypt(body, settings.JWE_SECRET),
            settings.JWT_SECRET,
            options={'verify_exp': False},
            algorithm='HS256'
        )
    except (jwt.InvalidTokenError, TypeError):
        raise AuthenticationFailed
    return payload
