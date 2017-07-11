# -*- coding: utf-8 -*-
import furl
import httpretty
import mock
from nose.tools import *  # flake8: noqa (PEP8 asserts)
import unittest

from framework.auth import cas

from tests.base import OsfTestCase, fake
from osf_tests.factories import UserFactory


def make_successful_response(user):
    return cas.CasResponse(
        authenticated=True,
        user=user._id,
        attributes={
            'accessToken': fake.md5()
        }
    )


def make_failure_response():
    return cas.CasResponse(
        authenticated=False,
        user=None,
    )


def make_external_response(release=True, unicode=False):
    attributes = {
            'accessToken': fake.md5(),
    }
    if release:
        attributes.update({
            'given-names': fake.first_name() if not unicode else u'нет',
            'family-name': fake.last_name() if not unicode else u'Да',
        })
    return cas.CasResponse(
        authenticated=True,
        user='OrcidProfile#{}'.format(fake.numerify('####-####-####-####')),
        attributes=attributes
    )


def generate_external_user_with_resp(service_url, user=True, release=True):
    """
    Generate mock user, external credential and cas response for tests.

    :param service_url: the service url
    :param user: set to `False` if user does not exists
    :param release: set to `False` if attributes are not released due to privacy settings
    :return: existing user object or new user, valid external credential, valid cas response
    """
    cas_resp = make_external_response(release=release)
    validated_credentials = cas.validate_external_credential(cas_resp.user)
    if user:
        user = UserFactory.build()
        user.external_identity = {
            validated_credentials['provider']: {
                validated_credentials['id']: 'VERIFIED'
            }
        }
        user.save()
        return user, validated_credentials, cas_resp
    else:
        user = {
            'external_id_provider': validated_credentials['provider'],
            'external_id': validated_credentials['id'],
            'fullname': validated_credentials['id'],
            'access_token': cas_resp.attributes['accessToken'],
            'service_url': service_url,
        }
        return user, validated_credentials, cas_resp

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
        user_id=user._id,
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

    @httpretty.activate
    def test_application_token_revocation_succeeds(self):
        url = self.client.get_auth_token_revocation_url()
        client_id= 'fake_id'
        client_secret = 'fake_secret'
        httpretty.register_uri(httpretty.POST,
                               url,
                               body={'client_id': client_id,
                                     'client_secret': client_secret},
                               status=204)

        res = self.client.revoke_application_tokens(client_id, client_secret)
        assert_equal(res, True)

    @httpretty.activate
    def test_application_token_revocation_fails(self):
        url = self.client.get_auth_token_revocation_url()
        client_id= 'fake_id'
        client_secret = 'fake_secret'
        httpretty.register_uri(httpretty.POST,
                               url,
                               body={'client_id': client_id,
                                     'client_secret': client_secret},
                               status=400)

        with assert_raises(cas.CasHTTPError):
            res = self.client.revoke_application_tokens(client_id, client_secret)

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

    @mock.patch('framework.auth.cas.get_user_from_cas_resp')
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_success(self, mock_service_validate, mock_get_user_from_cas_resp):
        mock_service_validate.return_value = make_successful_response(self.user)
        mock_get_user_from_cas_resp.return_value = (self.user, None, 'authenticate')
        ticket = fake.md5()
        service_url = 'http://localhost:5000/'
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(resp.status_code, 302)
        assert_equal(mock_service_validate.call_count, 1)
        assert_equal(mock_get_user_from_cas_resp.call_count, 1)

    @mock.patch('framework.auth.cas.get_user_from_cas_resp')
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_failure(self, mock_service_validate, mock_get_user_from_cas_resp):
        mock_service_validate.return_value = make_failure_response()
        mock_get_user_from_cas_resp.return_value = (None, None, None)
        ticket = fake.md5()
        service_url = 'http://localhost:5000/'
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(resp.status_code, 302)
        assert_equal(mock_service_validate.call_count, 1)
        assert_equal(mock_get_user_from_cas_resp.call_count, 0)

    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_invalidates_verification_key(self, mock_service_validate):
        self.user.verification_key = fake.md5()
        self.user.save()
        mock_service_validate.return_value = make_successful_response(self.user)
        ticket = fake.md5()
        service_url = 'http://localhost:5000/'
        resp = cas.make_response_from_ticket(ticket, service_url)
        self.user.reload()
        assert_true(self.user.verification_key is None)


class TestCASExternalLogin(OsfTestCase):

    def setUp(self):
        super(TestCASExternalLogin, self).setUp()
        self.user = UserFactory()

    def test_get_user_from_cas_resp_already_authorized(self):
        mock_response = make_external_response()
        validated_creds = cas.validate_external_credential(mock_response.user)
        self.user.external_identity = {
            validated_creds['provider']: {
                validated_creds['id']: 'VERIFIED'
            }
        }
        self.user.save()
        user, external_credential, action = cas.get_user_from_cas_resp(mock_response)
        assert_equal(user._id, self.user._id)
        assert_equal(external_credential, validated_creds)
        assert_equal(action, 'authenticate')

    def test_get_user_from_cas_resp_not_authorized(self):
        user, external_credential, action = cas.get_user_from_cas_resp(make_external_response())
        assert_equal(user, None)
        assert_true(external_credential is not None)
        assert_equal(action, 'external_first_login')

    @mock.patch('framework.auth.cas.get_user_from_cas_resp')
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_with_user(self, mock_service_validate, mock_get_user_from_cas_resp):
        mock_response = make_external_response()
        mock_service_validate.return_value = mock_response
        validated_creds = cas.validate_external_credential(mock_response.user)
        self.user.external_identity = {
            validated_creds['provider']: {
                validated_creds['id']: 'VERIFIED'
            }
        }
        self.user.save()
        mock_get_user_from_cas_resp.return_value = (self.user, validated_creds, 'authenticate')
        ticket = fake.md5()
        service_url = 'http://localhost:5000/'
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(mock_service_validate.call_count, 1)
        assert_true(mock_get_user_from_cas_resp.call_count, 1)
        assert_equal(resp.status_code, 302)
        assert_in('/logout?service=', resp.headers['Location'])
        assert_in('/login?service=', resp.headers['Location'])

    @mock.patch('framework.auth.cas.get_user_from_cas_resp')
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_no_user(self, mock_service_validate, mock_get_user_from_cas_resp):
        mock_response = make_external_response()
        mock_service_validate.return_value = mock_response
        validated_creds = cas.validate_external_credential(mock_response.user)
        mock_get_user_from_cas_resp.return_value = (None, validated_creds, 'external_first_login')
        ticket = fake.md5()
        service_url = 'http://localhost:5000/'
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(mock_service_validate.call_count, 1)
        assert_true(mock_get_user_from_cas_resp.call_count, 1)
        assert_equal(resp.status_code, 302)
        assert_equal(resp.location, '/external-login/email')

    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_generates_new_verification_key(self, mock_service_validate):
        self.user.verification_key = fake.md5()
        self.user.save()
        mock_response = make_external_response()
        validated_creds = cas.validate_external_credential(mock_response.user)
        self.user.external_identity = {
            validated_creds['provider']: {
                validated_creds['id']: 'VERIFIED'
            }
        }
        self.user.save()
        mock_service_validate.return_value = mock_response
        ticket = fake.md5()
        service_url = 'http://localhost:5000/'
        verification_key = self.user.verification_key
        resp = cas.make_response_from_ticket(ticket, service_url)
        self.user.reload()
        assert_not_equal(self.user.verification_key, verification_key)

    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_handles_unicode(self, mock_service_validate):
        mock_response = make_external_response(unicode=True)
        mock_service_validate.return_value = mock_response
        ticket = fake.md5()
        service_url = 'http://localhost:5000/'
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(resp.status_code, 302)
        assert_equal(mock_service_validate.call_count, 1)
        first_call_args = mock_service_validate.call_args[0]
        assert_equal(first_call_args[0], ticket)
        assert_equal(first_call_args[1], 'http://localhost:5000/')

    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_make_response_from_ticket_handles_non_unicode(self, mock_service_validate):
        mock_response = make_external_response()
        mock_service_validate.return_value = mock_response
        ticket = fake.md5()
        service_url = 'http://localhost:5000/'
        resp = cas.make_response_from_ticket(ticket, service_url)
        assert_equal(resp.status_code, 302)
        assert_equal(mock_service_validate.call_count, 1)
        first_call_args = mock_service_validate.call_args[0]
        assert_equal(first_call_args[0], ticket)
        assert_equal(first_call_args[1], 'http://localhost:5000/')
