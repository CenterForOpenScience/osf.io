import json
import httplib

import jwe
import jwt
from rest_framework.parsers import BaseParser
from rest_framework.exceptions import ParseError

from api.base import settings
from framework.exceptions import HTTPError

class InstitutionAuthParser(BaseParser):
    media_type = 'text/plain'

    def parse(self, stream, *args, **kwargs):
        value = stream.read().replace('-', '+').replace('_', '/')
        import ipdb; ipdb.set_trace()
        try:
            data = jwt.decode(
                jwe.decrypt(value, settings.JWE_SECRET),
                settings.JWT_SECRET,
                options={'verify_exp': False},
                algorithm='HS256'
            )
        except (jwt.InvalidTokenError, KeyError):
            raise HTTPError(httplib.FORBIDDEN)
        data['data'] = json.load(data['data'])
        import ipdb; ipdb.set_trace()
