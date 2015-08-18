import jwt

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase

from website import settings
from website.tokens import TokenHandler
from website.tokens.exceptions import TokenHandlerNotFound


class TestTokenHandler(OsfTestCase):

    def setUp(self):
        super(TestTokenHandler, self).setUp()

        self.payload = {
            'user_id': 'abc123',
            'field_x': 'xyzert'
        }
        self.secret = settings.JWT_SECRET
        self.encoded_token = jwt.encode(
            self.payload,
            self.secret,
            algorithm=settings.JWT_ALGORITHM)

    def test_encode(self):
        assert_equal(TokenHandler.encode(self.payload), self.encoded_token)

    def test_decode(self):
        assert_equal(TokenHandler.decode(self.encoded_token), self.payload)

    def test_from_string(self):
        token = TokenHandler.from_string(self.encoded_token)
        assert_equal(token.encoded_token, self.encoded_token)
        assert_equal(token.payload, self.payload)

    def test_from_payload(self):
        token = TokenHandler.from_payload(self.payload)
        assert_equal(token.encoded_token, self.encoded_token)
        assert_equal(token.payload, self.payload)

    def test_token_process_for_invalid_action_raises_TokenHandlerNotFound(self):
        self.payload['action'] = 'not a handler'
        token = TokenHandler.from_payload(self.payload)
        with assert_raises(TokenHandlerNotFound):
            token.process()

    @mock.patch('website.tokens.handlers.sanction_handler')
    def test_token_process_with_valid_action(self, mock_handler):
        self.payload['action'] = 'approve_registration_approval'
        token = TokenHandler.from_payload(self.payload)
        token.process()
        assert_true(
            mock_handler.called_with(
                'registration',
                'approve',
                self.payload,
                self.encoded_token
            )
        )
