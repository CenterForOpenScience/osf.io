from rest_framework.exceptions import ParseError

import jwe
import jwt

from api.base import settings
from api.cas import messages


def is_cas_request(request):
    """ Check if the request targets CAS endpoints.
    """
    return request.method == 'POST' and request.path.startswith('/v2/cas/')


def decrypt_request_body(request):
    """ Replace the JWE/JWT encrypted request body with the decrypted one.
    """

    request._body = decrypt_payload(request.body)


def decrypt_payload(payload):
    """
    Decrypt the payload.

    :param payload: the JWE/JwT encrypted payload
    :return: the decrypted json payload
    :raise: ParseError, Http 400
    """

    try:
        payload = jwt.decode(
            jwe.decrypt(payload, settings.JWE_SECRET),
            settings.JWT_SECRET,
            options={'verify_exp': False},
            algorithm='HS256'
        )
    except (AttributeError, TypeError,
            jwt.exceptions.InvalidTokenError, jwt.exceptions.InvalidKeyError, jwe.exceptions.PyJWEException):
        # TODO: inform Sentry, something is wrong with CAS/API or someone is trying to hack us
        raise ParseError(detail=messages.INVALID_REQUEST)

    return payload
