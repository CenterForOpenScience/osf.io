import jwt
import httplib as http

import mock
from nose.tools import *  # noqa
import unittest

from modularodm import Q

from tests.base import OsfTestCase
from tests import factories

from framework.exceptions import HTTPError

from website import settings
from website.models import Node, Sanction, Embargo, RegistrationApproval, Retraction
from website.tokens import decode, encode, TokenHandler
from website.tokens.exceptions import TokenHandlerNotFound

NO_SANCTION_MSG = 'There is no {0} associated with this token.'
APPROVED_MSG = "This registration is not pending {0}."
REJECTED_MSG = "This registration {0} has been rejected."

class MockAuth(object):

    def __init__(self, user):
        self.user = user        
        self.logged_in = True

mock_auth = lambda user: mock.patch('framework.auth.Auth.from_kwargs', mock.Mock(return_value=MockAuth(user)))

class TestTokenHandler(OsfTestCase):

    def setUp(self, *args, **kwargs):
        super(TestTokenHandler, self).setUp(*args, **kwargs)

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
        assert_equal(encode(self.payload), self.encoded_token)

    def test_decode(self):
        assert_equal(decode(self.encoded_token), self.payload)

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
            token.to_response()

    @mock.patch('website.tokens.handlers.sanction_handler')
    def test_token_process_with_valid_action(self, mock_handler):
        self.payload['action'] = 'approve_registration_approval'
        token = TokenHandler.from_payload(self.payload)
        token.to_response()
        assert_true(
            mock_handler.called_with(
                'registration',
                'approve',
                self.payload,
                self.encoded_token
            )
        )


SANCTION_CLASS_MAP = {
    'embargo': Embargo,
    'registration_approval': RegistrationApproval,
    'retraction': Retraction
}
SANCTION_FACTORY_MAP = {
    'embargo': factories.EmbargoFactory,
    'registration_approval': factories.RegistrationApprovalFactory,
    'retraction': factories.RetractionFactory
}

class SanctionTokenHandlerBase(OsfTestCase):

    kind = None

    def setUp(self, *args, **kwargs):
        OsfTestCase.setUp(self, *args, **kwargs)
        if not self.kind:
            return
        setattr(self, self.kind, SANCTION_FACTORY_MAP[self.kind]())
        setattr(self, '{0}_reg'.format(self.kind), Node.find_one(Q(self.kind, 'eq', getattr(self, self.kind))))
        setattr(self, '{0}_user'.format(self.kind), getattr(self, '{0}_reg'.format(self.kind)).creator)

    def test_sanction_handler(self):
        if not self.kind:
            return
        approval_token = getattr(self, self.kind).approval_state[getattr(self, '{}_user'.format(self.kind))._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        with mock_auth(getattr(self, '{0}_user'.format(self.kind))):
            with mock.patch('website.tokens.handlers.{0}_handler'.format(self.kind)) as mock_handler:
                handler.to_response()
                mock_handler.assert_called_with('approve', getattr(self, '{0}_reg'.format(self.kind)), getattr(self, '{0}_reg'.format(self.kind)).registered_from)

    def test_sanction_handler_no_sanction(self):
        if not self.kind:
            return
        approval_token = getattr(self, self.kind).approval_state[getattr(self, '{0}_user'.format(self.kind))._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        SANCTION_CLASS_MAP[self.kind].remove_one(getattr(self, self.kind))
        with mock_auth(getattr(self, '{0}_user'.format(self.kind))):
            try:
                handler.to_response()
            except HTTPError as e:
                assert_equal(e.code, http.BAD_REQUEST)
                assert_equal(e.data['message_long'], NO_SANCTION_MSG.format(SANCTION_CLASS_MAP[self.kind].DISPLAY_NAME))

    def test_sanction_handler_sanction_approved(self):
        if not self.kind:
            return
        approval_token = getattr(self, self.kind).approval_state[getattr(self, '{0}_user'.format(self.kind))._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        getattr(self, self.kind).state = Sanction.APPROVED
        getattr(self, self.kind).save()
        with mock_auth(getattr(self, '{0}_user'.format(self.kind))):
            try:
                handler.to_response()
            except HTTPError as e:
                assert_equal(e.code, http.BAD_REQUEST if self.kind in ['embargo', 'registration_approval'] else http.GONE)
                assert_equal(e.data['message_long'], APPROVED_MSG.format(getattr(self, self.kind).DISPLAY_NAME))

    def test_sanction_handler_sanction_rejected(self):
        if not self.kind:
            return
        approval_token = getattr(self, self.kind).approval_state[getattr(self, '{0}_user'.format(self.kind))._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        getattr(self, self.kind).state = Sanction.REJECTED
        getattr(self, self.kind).save()
        with mock_auth(getattr(self, '{0}_user'.format(self.kind))):
            try:
                handler.to_response()
            except HTTPError as e:
                assert_equal(e.code, http.GONE if self.kind in ['embargo', 'registration_approval'] else http.BAD_REQUEST)
                assert_equal(e.data['message_long'], REJECTED_MSG.format(getattr(self, self.kind).DISPLAY_NAME))

class TestEmbargoTokenHandler(SanctionTokenHandlerBase):

    kind = 'embargo'

class TestRegistrationApprovalTokenHandler(SanctionTokenHandlerBase):

    kind = 'registration_approval'

class TestRetractionTokenHandler(SanctionTokenHandlerBase):

    kind = 'retraction'
