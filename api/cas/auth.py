import json

import jwe
import jwt

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

from api.base import settings
from framework.auth.core import get_user


class CasAuthentication(BaseAuthentication):

    media_type = 'text/plain'

    def authenticate(self, request):

        payload = decrypt_payload(request.body)
        data = payload.get('data')
        # The JWT `data` payload is expected in the following structures
        # {
        #     "type": "LOGIN" | "REGISTER" | "INSTITUTION" | "EXTERNAL",
        #     "institutionProvider": {
        #         "idp": "",
        #         "id": "",
        #     },
        #     "externalIdentityProvider": {
        #         "idp": "",
        #         "id": "",
        #     },
        #     "user": {
        #         "username": "",
        #         "email": "",
        #         "passwordHash": "",
        #         "verificationKey": "",
        #         "middleNames": "",
        #         "familyName": "",
        #         "givenName": "",
        #         "fullname": "",
        #         "suffix": "",
        #     }
        # }

        if data.get('type') == "LOGIN":
            user, error_message = handle_login(data.get('user'))
            if user and not error_message:
                return user, None
            raise AuthenticationFailed(detail=error_message)
        elif data.get('REGISTER'):
            pass
        elif data.get('INSTITUTION'):
            pass
        elif data.get('EXTERNAL'):
            pass


def handle_login(data_user):

    email = data_user.get('email')
    verification_key = data_user.get('verificationKey')
    password_hash = data_user.get('passwordHash')
    if not email or not (verification_key or password_hash):
        return None, 'MISSING_CREDENTIAL'

    user = get_user(email)
    if not user:
        return None, 'ACCOUNT_NOT_FOUND'

    if verification_key:
        if verification_key == user.verification_key:
            return user, None
        return None, 'INVALID_VERIFICATION_KEY'

    if password_hash:
        if password_hash == user.password:
            return user, None
        return None, 'INVALID_PASSWORD'


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
