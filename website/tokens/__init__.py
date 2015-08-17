import functools

import jwt

from framework.auth.decorators import must_be_logged_in

from website import settings
from website.tokens import handlers
from website.tokens.exceptions import TokenHandlerNotFound

class TokenHandler(object):

    ACTION_MAP = {
        'approve_registration_approval': functools.partial(handlers.sanction_handler, 'registration', 'approve'),
        'reject_registration_approval': functools.partial(handlers.sanction_handler, 'registration', 'reject'),
        'approve_embargo': functools.partial(handlers.sanction_handler, 'embargo', 'approve'),
        'reject_embargo': functools.partial(handlers.sanction_handler, 'embargo', 'reject'),
        'approve_retraction': functools.partial(handlers.sanction_handler, 'retraction', 'approve'),
        'reject_retraction': functools.partial(handlers.sanction_handler, 'retraction', 'reject')
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
        return cls(encoded_token=encoded_token, payload=payload)

    @classmethod
    def from_token(cls, payload):
        encoded_token = TokenHandler.encode(payload)
        return cls(encoded_token=encoded_token, payload=payload)

    def process(self):
        action = self.payload.get('action', None)
        handler = self.ACTION_MAP.get(action)
        if handler:
            handler(self.payload, self.encoded_token)
        else:
            raise TokenHandlerNotFound(action=action)


@must_be_logged_in
def process_token(encoded_token, **kwargs):

    SUCCESS_MSG_MAP = {
        'approve_registration_approval': 'Your Registration approval has been accepted.',
        'reject_registration_approval': 'Your disapproval has been accepted and the registration has been cancelled.',
        'approve_embargo': 'Your Embargo approval has been accepted.',
        'reject_embargo': 'Your disapproval has been accepted and the embargo has been cancelled.',
        'approve_retraction': 'Your Retraction approval has been accepted.',
        'reject_retraction': 'Your disapproval has been accepted and the retraction has been cancelled.'
    }
    token = TokenHandler.from_string(encoded_token)
    token.process()

    return  SUCCESS_MSG_MAP.get(token.payload['action'], 'Your request has been accepted.')
