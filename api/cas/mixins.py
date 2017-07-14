import json

import jwe
import jwt

from rest_framework.exceptions import ParseError

from api.base import settings
from api.cas import messages

from framework import sentry


class APICASMixin(object):
    """ Mixin Class for API CAS Views.
    """

    def load_request_body_data(self, request):
        """
        Decrypt and decode the request body and return the data in json.

        :param request: the request
        :return: the decrypted body
        :raise: ParseError, Http 400
        """

        try:
            request.body = jwt.decode(
                jwe.decrypt(request.body, settings.JWE_SECRET),
                settings.JWT_SECRET,
                options={'verify_exp': False},
                algorithm='HS256'
            )
            return json.loads(request.body.get('data'))
        except (AttributeError, TypeError, jwt.exceptions.InvalidTokenError,
                jwt.exceptions.InvalidKeyError, jwe.exceptions.PyJWEException):
            sentry.log_message('Error: fail to decrypt or decode CAS request.')
            raise ParseError(detail=messages.INVALID_REQUEST)
