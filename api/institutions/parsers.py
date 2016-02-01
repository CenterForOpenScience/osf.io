import json
import httplib

import jwe
import jwt
from rest_framework.parsers import BaseParser

from api.base import settings
from framework.exceptions import HTTPError

class InstitutionAuthParser(BaseParser):
    media_type = 'text/plain'

    def parse(self, stream, *args, **kwargs):
        value = stream.read()
        try:
            data = jwt.decode(
                jwe.decrypt(value, settings.JWE_SECRET),
                settings.JWT_SECRET,
                options={'verify_exp': False},
                algorithm='HS256'
            )
        except (jwt.InvalidTokenError, KeyError):
            raise HTTPError(httplib.FORBIDDEN)

        username = data['sub']
        data = json.loads(data['data'])

        return {'username': username, 'data': data}
