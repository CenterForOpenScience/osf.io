from rest_framework import status as http_status
import functools
import jwt
from flask import request

from framework.exceptions import HTTPError

from website import settings
from osf.utils.tokens import handlers
from osf.exceptions import TokenHandlerNotFound

class TokenHandler(object):

    HANDLERS = {
        'approve_registration_approval': functools.partial(handlers.sanction_handler, 'registration', 'approve'),
        'reject_registration_approval': functools.partial(handlers.sanction_handler, 'registration', 'reject'),
        'approve_embargo': functools.partial(handlers.sanction_handler, 'embargo', 'approve'),
        'reject_embargo': functools.partial(handlers.sanction_handler, 'embargo', 'reject'),
        'approve_embargo_termination_approval': functools.partial(handlers.sanction_handler, 'embargo_termination_approval', 'approve'),
        'reject_embargo_termination_approval': functools.partial(handlers.sanction_handler, 'embargo_termination_approval', 'reject'),
        'approve_retraction': functools.partial(handlers.sanction_handler, 'retraction', 'approve'),
        'reject_retraction': functools.partial(handlers.sanction_handler, 'retraction', 'reject')
    }

    def __init__(self, encoded_token=None, payload=None):

        self.encoded_token = encoded_token
        self.payload = payload

    @classmethod
    def from_string(cls, encoded_token):
        try:
            payload = decode(encoded_token)
        except jwt.DecodeError as e:
            raise HTTPError(
                http_status.HTTP_400_BAD_REQUEST,
                data={
                    'message_short': 'Bad request',
                    'message_long': e.message
                }
            )
        return cls(encoded_token=encoded_token, payload=payload)

    @classmethod
    def from_payload(cls, payload):
        encoded_token = encode(payload)
        return cls(encoded_token=encoded_token, payload=payload)

    def to_response(self):
        action = self.payload.get('action', None)
        handler = self.HANDLERS.get(action)
        if handler:
            return handler(self.payload, self.encoded_token)
        else:
            raise TokenHandlerNotFound(action=action)


def process_token_or_pass(func):
    """Parse encoded token and run attached handlers (if any).

    Note: this method may cause redirects, 4XX status codes, and other
    potentially unexpected behavior. If there's a token attached to the
    URL you are developing or debugging (i.e. ?token=SOME_TOKEN), this
    method may be intercepting/short-circuting your view logic.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        encoded_token = request.args.get('token')
        if encoded_token:
            handler = TokenHandler.from_string(encoded_token)
            try:
                res = handler.to_response()
            except TokenHandlerNotFound as e:
                raise HTTPError(
                    http_status.HTTP_400_BAD_REQUEST,
                    data={
                        'message_short': 'Invalid Token',
                        'message_long': 'No token handler for action: {} found'.format(e.action)
                    }
                )
            if res:
                return res
        return func(*args, **kwargs)
    return wrapper


def encode(payload):
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )


def decode(encoded_token):
    return jwt.decode(
        encoded_token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM])
