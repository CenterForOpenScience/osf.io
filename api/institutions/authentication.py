import json

import jwe
import jwt

from django.utils import timezone

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from api.base import settings

from framework.auth import get_or_create_user

from website.models import Institution
from website.mails import send_mail, WELCOME_OSF4I


class InstitutionAuthentication(BaseAuthentication):

    media_type = 'text/plain'

    def authenticate(self, request):
        """
        Handle CAS institution authentication request.

        The JWT `data` payload is expected in the following structure:
        {
            "provider": {
                "idp":  "",
                "id":   "",
                "user": {
                    "username":     "",
                    "fullname":     "",
                    "familyName":   "",
                    "givenName":    "",
                    "middleNames":  "",
                    "suffix":       "",
                }
            }
        }

        :param request: the POST request
        :return: user, None if authentication succeed
        :raises: AuthenticationFailed if authentication fails
        """

        try:
            payload = jwt.decode(
                jwe.decrypt(request.body, settings.JWE_SECRET),
                settings.JWT_SECRET,
                options={'verify_exp': False},
                algorithm='HS256'
            )
        except (jwt.InvalidTokenError, TypeError):
            raise AuthenticationFailed

        data = json.loads(payload['data'])
        provider = data['provider']

        institution = Institution.load(provider['id'])
        if not institution:
            raise AuthenticationFailed('Invalid institution id specified "{}"'.format(provider['id']))

        username = provider['user'].get('username')
        fullname = provider['user'].get('fullname')
        given_name = provider['user'].get('givenName')
        family_name = provider['user'].get('familyName')

        # use given name and family name to build full name if not provided
        if given_name and family_name and not fullname:
            fullname = given_name + ' ' + family_name

        # use username if no names are provided
        if not fullname:
            fullname = username

        user, created = get_or_create_user(fullname, username, reset_password=False)

        if created:
            # `get_or_create_user()` guesses given name and family name from fullname
            # replace the guessed ones if the names are provided from the authentication request
            if given_name:
                user.given_name = given_name
            if family_name:
                user.family_name = family_name
            user.middle_names = provider['user'].get('middleNames')
            user.suffix = provider['user'].get('suffix')
            user.date_last_login = timezone.now()

            # save and register user
            # a user must be saved in order to have a valid `guid___id`
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
