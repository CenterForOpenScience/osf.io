import functools

import jwt

from framework.auth.decorators import must_be_logged_in

from website import settings
from website.tokens import handlers
from website.tokens.exceptions import TokenHandlerNotFound

class TokenHandler(object):

    ACTION_MAP = {
        'registration_approval': functools.partial(handlers.sanction_handler, 'registration', 'approve'),
        'registration_rejection': functools.partial(handlers.sanction_handler, 'registration', 'reject'),
        'embargo_approval': functools.partial(handlers.sanction_handler, 'embargo', 'approve'),
        'embargo_rejection': functools.partial(handlers.sanction_handler, 'embargo', 'reject'),
        'retraction_approval': functools.partial(handlers.sanction_handler, 'retraction', 'approve'),
        'retraction_rejection': functools.partial(handlers.sanction_handler, 'retraction', 'reject')
    }

    def __init__(self, encoded_token=None, payload=None):

        self.encoded_token = encoded_token
        self.payload = payload

    @staticmethod
    def encode(payload):
        return jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm='HS256'
        )

    @staticmethod
    def decode(encoded_token):
        return jwt.decode(encoded_token, settings.JWT_SECRET, algorithms=['HS256'])

    @classmethod
    def from_string(cls, encoded_token):
        payload = TokenHandler.decode(encoded_token)
        return cls(raw_token=encoded_token, payload=payload)

    @classmethod
    def from_token(cls, payload):
        encoded_token = TokenHandler.encode(payload)
        return cls(raw_token=encoded_token, payload=payload)

    def process(self):
        action = self.payload.get('action', None)
        handler = self.ACTION_MAP.get(action)
        if handler:
            handler(self.payload, self.encoded_token)
        else:
            raise TokenHandlerNotFound(action=action)


@must_be_logged_in
def process_token(encoded_token, **kwargs):

    token = TokenHandler.from_string(encoded_token)
    try:
        token.process()
    # TODO(hrybacki): expand this exception
    except Exception:
        pass
