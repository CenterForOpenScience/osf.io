import json

import jwe
import jwt

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

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
                    if error_message:
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
                if error_message:
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
    if not email or not (remote_authenticated or verification_key or password):
        return None, 'MISSING_CREDENTIALS'

    user = OSFUser.objects.filter(Q(username=email) | Q(emails__icontains=email)).first()
    if not user:
        return None, 'ACCOUNT_NOT_FOUND'

    if remote_authenticated:
        return user, None

    if verification_key:
        if verification_key == user.verification_key:
            return user, None
        return None, 'INVALID_VERIFICATION_KEY'

    if password:
        if user.check_password(password):
            return user, None
        return None, 'INVALID_PASSWORD'


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
        return 'TWO_FACTOR_AUTHENTICATION_REQUIRED'

    two_factor = get_user_with_two_factor(user)
    if two_factor and two_factor.verify_code(one_time_password):
        return None
    return 'INVALID_ONE_TIME_PASSWORD'


# TODO: OSF user status is quite complicated, which sometimes requires more than one status below to decide.
# TODO: Revisit this part when switching to Django-OSF
def verify_user_status(user):
    # An active user must be registered, claimed, not disabled, not merged and has a not null/None password.
    # Only active user can passes the verification.
    if user.is_active:
        return None

    # If the user instance is not claimed, it is also not registered. It can be either a contributor or a new user
    # pending confirmation.
    if not user.is_claimed and not user.is_registered:
        # If the user instance has a null/None password, it must be an unclaimed contributor.
        # TODO: For now, this case cannot be reached by normal authentication flow given no password.
        # TODO: For now, it is possible for the user to register before claim the account.
        if not user.password:
            return 'USER_NOT_CLAIMED'
        # If the user instance has a password, it must be a unconfirmed user who registered for a new account.
        # When the user tries to login, a message for he/she to check the confirmation email with the option of
        # resending confirmation is displayed.
        return 'USER_NOT_CONFIRMED'

    # If the user instance is merged by another user, it is registered and claimed. However, its username and
    # password fields are both null/None.
    # TODO: For now, this case cannot be reached by normal authentication flow given no username and password.
    if user.is_merged and user.is_registered and user.is_claimed:
        return 'USER_MERGED'

    # If the user instance is disabled, it is also not registered. However, it still has the username and password.
    # When the user tries to login, an account disabled message will be displayed.
    if user.is_disabled and not user.is_registered and user.is_claimed:
        return 'USER_DISABLED'

    # If the status does not meet any of the above criteria, return `USER_NOT_ACTIVE` and ask the user to contact OSF.
    return 'USER_NOT_ACTIVE'


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
