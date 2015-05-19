# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # flake8: noqa (PEP8 asserts)

from framework.auth import cas

from tests.base import OsfTestCase, fake
from tests.factories import UserFactory

def make_successful_response(user):
    return cas.CasResponse(
        authenticated=True, user=user._primary_key,
        attributes={
            'accessToken': fake.md5()
        }
    )

def make_failure_response():
    return cas.CasResponse(
        authenticated=False, user=None,
    )


# TODO:
class TestCASClient(OsfTestCase):
    pass

class TestCASTicketAuthentication(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory()

    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_success(self, mock_service_validate):
        mock_response = make_successful_response(self.user)
        mock_service_validate.return_value = mock_response
        ticket = fake.md5()
        service_url = 'http://accounts.osf.io/?ticket=' + ticket
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(resp.status_code, 302)
        mock_service_validate.assert_called_once()
        first_call_args = mock_service_validate.call_args[0]
        assert_equal(first_call_args[0], ticket)
        assert_equal(first_call_args[1], 'http://accounts.osf.io/')

    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_failure(self, mock_service_validate):
        mock_response = make_failure_response()
        mock_service_validate.return_value = mock_response
        ticket = fake.md5()
        service_url = 'http://accounts.osf.io/?ticket=' + ticket
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(resp.status_code, 302)
        assert_equal(resp.location, 'http://accounts.osf.io/')

    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_invalidates_verification_key(self, mock_service_validate):
        self.user.verification_key = fake.md5()
        self.user.save9)
        mock_response = make_successful_response(self.user)
        mock_service_validate.return_value = mock_response
        ticket = fake.md5()
        service_url = 'http://accounts.osf.io/?ticket=' + ticket
        resp = cas.make_response_from_ticket(ticket, service_url)
