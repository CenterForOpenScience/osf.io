import jwt
import httplib as http

import mock
from nose.tools import *  # noqa
from nose.loader import TestLoader
import nose

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

def make_sanction_token_handler_case(kind):

    def setUp(self, *args, **kwargs):
        OsfTestCase.setUp(self, *args, **kwargs)
        setattr(self, kind, SANCTION_FACTORY_MAP[kind]())
        setattr(self, '{0}_reg'.format(kind), Node.find_one(Q(kind, 'eq', getattr(self, kind))))
        setattr(self, '{0}_user'.format(kind), getattr(self, '{0}_reg'.format(kind)).creator)

    @mock.patch('website.tokens.handlers.{0}_handler'.format(kind))
    def test_sanction_handler(self, mock_handler):
        approval_token = getattr(self, kind).approval_state[getattr(self, '{}_user'.format(kind))._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        with mock_auth(getattr(self, '{0}_user'.format(kind))):
            handler.to_response()
            mock_handler.assert_called_with('approve', getattr(self, '{0}_reg'.format(kind)), getattr(self, '{0}_reg'.format(kind)).registered_from)

    def test_sanction_handler_no_sanction(self):
        approval_token = getattr(self, kind).approval_state[getattr(self, '{0}_user'.format(kind))._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        SANCTION_CLASS_MAP[kind].remove_one(getattr(self, kind))
        with mock_auth(getattr(self, '{0}_user'.format(kind))):
            try:
                handler.to_response()
            except HTTPError as e:
                assert_equal(e.code, http.BAD_REQUEST)
                assert_equal(e.data['message_long'], NO_SANCTION_MSG.format(SANCTION_CLASS_MAP[kind].DISPLAY_NAME))

    def test_sanction_handler_sanction_approved(self):
        approval_token = getattr(self, kind).approval_state[getattr(self, '{0}_user'.format(kind))._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        getattr(self, kind).state = Sanction.APPROVED
        getattr(self, kind).save()
        with mock_auth(getattr(self, '{0}_user'.format(kind))):
            try:
                handler.to_response()
            except HTTPError as e:
                assert_equal(e.code, http.BAD_REQUEST if kind in ['embargo', 'registration_approval'] else http.GONE)
                assert_equal(e.data['message_long'], APPROVED_MSG.format(getattr(self, kind).DISPLAY_NAME))

    def test_sanction_handler_sanction_rejected(self):
        approval_token = getattr(self, kind).approval_state[getattr(self, '{0}_user'.format(kind))._id]['approval_token']
        handler = TokenHandler.from_string(approval_token)
        getattr(self, kind).state = Sanction.REJECTED
        getattr(self, kind).save()
        with mock_auth(getattr(self, '{0}_user'.format(kind))):
            try:
                handler.to_response()
            except HTTPError as e:
                assert_equal(e.code, http.GONE if kind in ['embargo', 'registration_approval'] else http.BAD_REQUEST)
                assert_equal(e.data['message_long'], REJECTED_MSG.format(getattr(self, kind).DISPLAY_NAME))

    return type(
        'Test{0}TokenHandlers'.format(kind),
        (OsfTestCase,),
        {
            'setUp': setUp,
            'test_sanction_handler_{0}'.format(kind): test_sanction_handler,
            'test_sanction_sanction_handler_no_{0}'.format(kind): test_sanction_handler_no_sanction,
            'test_sanction_handler_{0}_approved'.format(kind): test_sanction_handler_sanction_approved,
            'test_sanction_handler_{0}_rejected'.format(kind): test_sanction_handler_sanction_rejected
        }
    )

global test_sanction_handler_embargo
global test_sanction_handler_registration_appproval
global test_sanction_handler_retraction
for kind in ['embargo', 'registration_approval', 'retraction']:
    globals()['test_sanction_handler_{0}'.format(kind)] = make_sanction_token_handler_case(kind)

if __name__ == '__main__':
    unittest.main()
