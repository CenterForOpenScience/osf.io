import json

import jwe
import jwt

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from api.base import settings
from website.models import Institution
from framework.auth import get_or_create_user


class InstitutionAuthentication(BaseAuthentication):
    media_type = 'text/plain'

    def authenticate(self, request):
        try:
            payload = jwt.decode(
                jwe.decrypt(request.body, settings.JWE_SECRET),
                settings.JWT_SECRET,
                options={'verify_exp': False},
                algorithm='HS256'
            )
        except (jwt.InvalidTokenError, TypeError):
            raise AuthenticationFailed

        # The JWT `data` payload is expected in the following structure.
        #
        # {"provider": {
        #     "idp": "https://login.circle.edu/idp/shibboleth",
        #     "id": "CIR",
        #     "user": {
        #         "middleNames": "",
        #         "familyName": "",
        #         "givenName": "",
        #         "fullname": "Circle User",
        #         "suffix": "",
        #         "username": "user@circle.edu"
        #     }
        # }}
        data = json.loads(payload['data'])
        provider = data['provider']

        institution = Institution.load(provider['id'])
        if not institution:
            raise AuthenticationFailed('Invalid institution id specified "{}"'.format(provider['id']))

        username = provider['user']['username']
        fullname = provider['user']['fullname']

        user, created = get_or_create_user(fullname, username)

        if created:
            user.given_name = provider['user'].get('givenName')
            user.middle_names = provider['user'].get('middleNames')
            user.family_name = provider['user'].get('familyName')
            user.suffix = provider['user'].get('suffix')
            user.save()

            # User must be saved in order to have a valid _id
            user.register(username)

        if institution not in user.affiliated_institutions:
            user.affiliated_institutions.append(institution)
            user.save()

        return user, None
