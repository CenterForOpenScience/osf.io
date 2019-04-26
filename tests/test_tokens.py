import jwt
from rest_framework import status as http_status

import mock
from django.db.models import Q
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from osf_tests import factories
from tests.utils import mock_auth

from framework.exceptions import HTTPError

from website import settings
from osf.models import AbstractNode, Embargo, RegistrationApproval, Retraction, Sanction
from osf.utils.tokens import decode, encode, TokenHandler
from osf.exceptions import TokenHandlerNotFound

NO_SANCTION_MSG = 'There is no {0} associated with this token.'
APPROVED_MSG = 'This registration is not pending {0}.'
REJECTED_MSG = 'This registration {0} has been rejected.'

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

    @mock.patch('osf.utils.tokens.handlers.sanction_handler')
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

class SanctionTokenHandlerBase(OsfTestCase):

    kind = None
    Model = None
    Factory = None

    def setUp(self, *args, **kwargs):
        OsfTestCase.setUp(self, *args, **kwargs)
        if not self.kind:
            return
        self.sanction = self.Factory()
        self.reg = AbstractNode.objects.get(Q(**{self.Model.SHORT_NAME: self.sanction}))
        self.user = self.reg.creator

    def test_sanction_handler(self):
        if not self.kind:
            return
        approval_token = self.sanction.approval_state[self.user._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        with mock_auth(self.user):
            with mock.patch('osf.utils.tokens.handlers.{0}_handler'.format(self.kind)) as mock_handler:
                handler.to_response()
                mock_handler.assert_called_with('approve', self.reg, self.reg.registered_from)

    def test_sanction_handler_no_sanction(self):
        if not self.kind:
            return
        approval_token = self.sanction.approval_state[self.user._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        self.Model.delete(self.sanction)
        with mock_auth(self.user):
            try:
                handler.to_response()
            except HTTPError as e:
                assert_equal(e.code, http_status.HTTP_400_BAD_REQUEST)
                assert_equal(e.data['message_long'], NO_SANCTION_MSG.format(self.Model.DISPLAY_NAME))

    def test_sanction_handler_sanction_approved(self):
        if not self.kind:
            return
        approval_token = self.sanction.approval_state[self.user._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        self.sanction.state = Sanction.APPROVED
        self.sanction.save()
        with mock_auth(self.user):
            try:
                handler.to_response()
            except HTTPError as e:
                assert_equal(e.code, http_status.HTTP_400_BAD_REQUEST if self.kind in ['embargo', 'registration_approval'] else http_status.HTTP_410_GONE)
                assert_equal(e.data['message_long'], APPROVED_MSG.format(self.sanction.DISPLAY_NAME))

    def test_sanction_handler_sanction_rejected(self):
        if not self.kind:
            return
        approval_token = self.sanction.approval_state[self.user._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        self.sanction.state = Sanction.REJECTED
        self.sanction.save()
        with mock_auth(self.user):
            try:
                handler.to_response()
            except HTTPError as e:
                assert_equal(e.code, http_status.HTTP_410_GONE if self.kind in ['embargo', 'registration_approval'] else http_status.HTTP_400_BAD_REQUEST)
                assert_equal(e.data['message_long'], REJECTED_MSG.format(self.sanction.DISPLAY_NAME))

class TestEmbargoTokenHandler(SanctionTokenHandlerBase):

    kind = 'embargo'
    Model = Embargo
    Factory = factories.EmbargoFactory

class TestRegistrationApprovalTokenHandler(SanctionTokenHandlerBase):

    kind = 'registration_approval'
    Model = RegistrationApproval
    Factory = factories.RegistrationApprovalFactory

class TestRetractionTokenHandler(SanctionTokenHandlerBase):

    kind = 'retraction'
    Model = Retraction
    Factory = factories.RetractionFactory
