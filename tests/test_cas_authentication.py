# -*- coding: utf-8 -*-
import mock
import unittest
from nose.tools import *  # flake8: noqa (PEP8 asserts)
import httpretty
import furl

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

RESPONSE_TEMPLATE = """
<cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
    <cas:authenticationSuccess>
        <cas:user>{user_id}</cas:user>
            <cas:attributes>
                        <cas:isFromNewLogin>true</cas:isFromNewLogin>
                        <cas:authenticationDate>Tue May 19 02:20:19 UTC 2015</cas:authenticationDate>
                        <cas:givenName>{given_name}</cas:givenName>
                        <cas:familyName>{family_name}</cas:familyName>
                        <cas:longTermAuthenticationRequestTokenUsed>true</cas:longTermAuthenticationRequestTokenUsed>
                        <cas:accessToken>{access_token}</cas:accessToken>
                        <cas:username>{username}</cas:username>
            </cas:attributes>
    </cas:authenticationSuccess>
</cas:serviceResponse>
"""
def make_service_validation_response_body(user, access_token=None):
    token = access_token or fake.md5()
    return RESPONSE_TEMPLATE.format(
        user_id=user._primary_key,
        given_name=user.given_name,
        family_name=user.family_name,
        username=user.username,
        access_token=token
    )


def test_parse_authorization_header():
    token = fake.md5()
    valid = 'Bearer {}'.format(token)
    assert_equal(cas.parse_auth_header(valid), token)

    missing_token = 'Bearer '
    with assert_raises(cas.CasTokenError):
        cas.parse_auth_header(missing_token)


# TODO:
class TestCASClient(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.base_url = 'http://accounts.test.test'
        self.client = cas.CasClient(self.base_url)

    @httpretty.activate
    def test_service_validate(self):
        user = UserFactory()
        url = furl.furl(self.base_url)
        url.path.segments.extend(('p3', 'serviceValidate',))
        service_url = 'http://test.osf.io'
        ticket = fake.md5()
        body = make_service_validation_response_body(user, ticket)
        httpretty.register_uri(
            httpretty.GET,
            url.url,
            body=body,
            status=200,
        )
        resp = self.client.service_validate(ticket, service_url)
        assert_true(resp.authenticated)

    @httpretty.activate
    def test_service_validate_invalid_ticket_raises_error(self):
        url = furl.furl(self.base_url)
        url.path.segments.extend(('p3', 'serviceValidate',))
        service_url = 'http://test.osf.io'
        # Return error response
        httpretty.register_uri(
            httpretty.GET,
            url.url,
            body='invalid ticket...',
            status=500,
        )
        with assert_raises(cas.CasHTTPError):
            self.client.service_validate('invalid', service_url)

    @httpretty.activate
    def test_profile_invalid_access_token_raises_error(self):
        url = furl.furl(self.base_url)
        url.path.segments.extend(('oauth2', 'profile',))
        httpretty.register_uri(
            httpretty.GET,
            url.url,
            status=500,
        )
        with assert_raises(cas.CasHTTPError):
            self.client.profile('invalid-access-token')

    @unittest.skip('finish me')
    def test_profile_valid_access_token_returns_cas_response(self):
        assert 0

    @unittest.skip('finish me')
    def test_get_login_url(self):
        assert 0

    @unittest.skip('finish me')
    def test_get_logout_url(self):
        assert 0


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
        self.user.save()
        mock_response = make_successful_response(self.user)
        mock_service_validate.return_value = mock_response
        ticket = fake.md5()
        service_url = 'http://accounts.osf.io/?ticket=' + ticket
        resp = cas.make_response_from_ticket(ticket, service_url)
