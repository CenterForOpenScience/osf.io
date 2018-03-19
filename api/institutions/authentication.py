import json

import jwe
import jwt

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from api.base import settings

from framework import sentry
from framework.auth import get_or_create_user

from osf.models import Institution
from website.mails import send_mail, WELCOME_OSF4I
from website.settings import OSF_CONTACT_EMAIL


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
                user=user,
                osf_contact_email=OSF_CONTACT_EMAIL
            )

        if not user.is_affiliated_with_institution(institution):
            user.affiliated_institutions.add(institution)
            user.save()

        return user, None
