import json

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from django.db.models import Q
from django.utils import timezone

from api.cas import util

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
            user, error_message = handle_login(data.get('user'))
            if user and not error_message:
                error_message = util.get_user_status(user)
                if error_message != util.USER_ACTIVE:
                    raise AuthenticationFailed(detail=error_message)
                return user, None
            raise AuthenticationFailed(detail=error_message)

        if data.get('type') == 'REGISTER':
            user, error_message = handle_register(data.get('user'))
            if user and not error_message:
                return user, None
            raise AuthenticationFailed(detail=error_message)

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


def handle_login(data_user):

    email = data_user.get('email')
    remote_authenticated = data_user.get('remoteAuthenticated')
    verification_key = data_user.get('verificationKey')
    password = data_user.get('password')
    one_time_password = data_user.get('oneTimePassword')

    # check if credentials are provided
    if not email or not (remote_authenticated or verification_key or password):
        return None, util.MISSING_CREDENTIALS

    # retrieve the user
    user = OSFUser.objects.filter(Q(username=email) | Q(emails__icontains=email)).first()
    if not user:
        return None, util.ACCOUNT_NOT_FOUND

    # verify user status
    if util.get_user_status(user) == util.USER_NOT_CLAIMED:
        return None, util.USER_NOT_CLAIMED

    # by remote authentication
    if remote_authenticated:
        return user, util.verify_two_factor(user, one_time_password)

    # by verification key
    if verification_key:
        if verification_key == user.verification_key:
            return user, util.verify_two_factor(user, one_time_password)
        return None, util.INVALID_VERIFICATION_KEY

    # by password
    if password:
        if user.check_password(password):
            return user, util.verify_two_factor(user, one_time_password)
        return None, util.INVALID_PASSWORD


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
