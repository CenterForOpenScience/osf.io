import json

import jwe
import jwt
import waffle

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from api.base import settings

from framework import sentry
from framework.auth import get_or_create_user

from osf import features
from osf.models import Institution
from website.mails import send_mail, WELCOME_OSF4I
from website.settings import OSF_SUPPORT_EMAIL, DOMAIN


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
                algorithm='HS256',
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
            # User with the matching institution email has not been not found.  The above method
            # ``get_or_create_user()`` creates a new confirmed (but yet to be active) user with a
            # random password using  ``password = str(uuid.uuid4())``.

            # Update user profile
            if given_name:
                user.given_name = given_name
            if family_name:
                user.family_name = family_name
            if middle_names:
                user.middle_names = middle_names
            if suffix:
                user.suffix = suffix
            user.update_date_last_login()

            # Relying on front-end validation until `accepted_tos` is added to the JWT payload
            user.accepted_terms_of_service = timezone.now()

            # Save and register user, after which the confirmed user become active.
            user.save()
            user.register(username)

            # Send confirmation email
            send_mail(
                to_addr=user.username,
                mail=WELCOME_OSF4I,
                mimetype='html',
                user=user,
                domain=DOMAIN,
                osf_support_email=OSF_SUPPORT_EMAIL,
                storage_flag_is_active=waffle.flag_is_active(request, features.STORAGE_I18N),
            )
        elif not user.is_active:
            # An existing user object has been found with the matching institution email.  If the
            # user turns out to be an inactive one (e.g. unclaimed, unconfirmed, etc.), however,
            # simply send a sentry message and return the user.  DON'T affiliate the institution.
            # CAS will handle the rest and inform the institution user.
            sentry.log_message('The authenticated institution user is inactive: '
                               'user={}, inst={}'.format(username, provider['id']))
            return user, None

        if not user.is_affiliated_with_institution(institution):
            user.affiliated_institutions.add(institution)
            user.save()

        return user, None
