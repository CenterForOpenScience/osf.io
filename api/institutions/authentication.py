import json

import jwe
import jwt

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from rest_framework.exceptions import NotFound
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from api.base import settings
from website.models import Institution
from framework.auth import get_or_create_user


def find_institution_by_domain(username):
    domain = username.split('@')[1]
    try:
        inst = Institution.find_one(Q('domains', 'eq', domain.lower()))
    except NoResultsFound:
        raise NotFound
    return inst


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
        except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
            raise AuthenticationFailed

        username = payload['sub']
        data = json.loads(payload['data'])

        institution = find_institution_by_domain(username)
        fullname = data.get(institution.metadata_request_fields.get('fullname'))

        user, created = get_or_create_user(fullname, username)

        if institution not in user.affiliated_institutions:
            user.affiliated_institutions.append(institution)

        user.institutions_metadata.setdefault(institution._id, {}).update(data)
        user.save()

        if created:
            # User has to be saved to have a valid _id
            user.register(username)
            user.save()

        return user, None
