from datetime import datetime
from rest_framework import status as http_status
import logging
import json
import logging
import mock
import time
from future.moves.urllib.parse import urlparse, urljoin, parse_qs

import responses
from nose.tools import *  # noqa
import pytz
from oauthlib.oauth2 import OAuth2Error
from requests_oauthlib import OAuth2Session

from framework.auth import authenticate
from framework.exceptions import PermissionsError, HTTPError
from framework.sessions import session
from osf.models.external import ExternalAccount, ExternalProvider, OAUTH1, OAUTH2
from website.settings import ADDONS_OAUTH_NO_REDIRECT
from website.util import api_url_for, web_url_for

from tests.base import OsfTestCase
from osf_tests.factories import (
    AuthUserFactory,
    ExternalAccountFactory,
    MockOAuth2Provider,
    UserFactory,
)

SILENT_LOGGERS = ['oauthlib', 'requests_oauthlib']

for logger in SILENT_LOGGERS:
    logging.getLogger(logger).setLevel(logging.ERROR)


class MockOAuth1Provider(ExternalProvider):
    _oauth_version = OAUTH1
    name = 'Mock OAuth 1.0a Provider'
    short_name = 'mock1a'

    client_id = 'mock1a_client_id'
    client_secret = 'mock1a_client_secret'

    auth_url_base = 'http://mock1a.com/auth'
    request_token_url = 'http://mock1a.com/request'
    callback_url = 'http://mock1a.com/callback'

    def handle_callback(self, response):
        return {
            'provider_id': 'mock_provider_id'
        }


def _prepare_mock_oauth2_handshake_response(expires_in=3600):

    responses.add(
        responses.Response(
            responses.POST,
            'https://mock2.com/callback',
            body=json.dumps({
                'access_token': 'mock_access_token',
                'expires_at': time.time() + expires_in,
                'expires_in': expires_in,
                'refresh_token': 'mock_refresh_token',
                'scope': ['all'],
                'token_type': 'bearer',
            }),
            status=200,
            content_type='application/json',
        )
    )

def _prepare_mock_500_error():
    responses.add(
        responses.Response(
            responses.POST,
            'https://mock2.com/callback',
            body='{"error": "not found"}',
            status=503,
            content_type='application/json',
        )
    )

def _prepare_mock_401_error():
    responses.add(
        responses.Response(
            responses.POST,
            'https://mock2.com/callback',
            body='{"error": "user denied access"}',
            status=401,
            content_type='application/json',
        )
    )

class TestExternalAccount(OsfTestCase):
    # Test the ExternalAccount object and associated views.
    #
    # Functionality not specific to the OAuth version used by the
    # ExternalProvider should go here.

    def setUp(self):
        super(TestExternalAccount, self).setUp()
        self.user = AuthUserFactory()
        self.provider = MockOAuth2Provider()

    def test_disconnect(self):
        # Disconnect an external account from a user
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
        )
        self.user.external_accounts.add(external_account)
        self.user.save()

        # If the external account isn't attached, this test has no meaning
        assert_equal(ExternalAccount.objects.all().count(), 1)
        assert_in(
            external_account,
            self.user.external_accounts.all(),
        )

        response = self.app.delete(
            api_url_for('oauth_disconnect',
                        external_account_id=external_account._id),
            auth=self.user.auth
        )

        # Request succeeded
        assert_equal(
            response.status_code,
            http_status.HTTP_200_OK,
        )

        self.user.reload()
        # external_account.reload()

        # External account has been disassociated with the user
        assert_not_in(
            external_account,
            self.user.external_accounts.all(),
        )

        # External account is still in the database
        assert_equal(ExternalAccount.objects.all().count(), 1)

    def test_disconnect_with_multiple_connected(self):
        # Disconnect an account connected to multiple users from one user
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
        )
        self.user.external_accounts.add(external_account)
        self.user.save()

        other_user = UserFactory()
        other_user.external_accounts.add(external_account)
        other_user.save()

        response = self.app.delete(
            api_url_for('oauth_disconnect',
                        external_account_id=external_account._id),
            auth=self.user.auth
        )

        # Request succeeded
        assert_equal(
            response.status_code,
            http_status.HTTP_200_OK,
        )

        self.user.reload()

        # External account has been disassociated with the user
        assert_not_in(
            external_account,
            self.user.external_accounts.all(),
        )

        # External account is still in the database
        assert_equal(ExternalAccount.objects.all().count(), 1)

        other_user.reload()

        # External account is still associated with the other user
        assert_in(
            external_account,
            other_user.external_accounts.all(),
        )


class TestExternalProviderOAuth1(OsfTestCase):
    # Test functionality of the ExternalProvider class, for OAuth 1.0a

    def setUp(self):
        super(TestExternalProviderOAuth1, self).setUp()
        self.user = UserFactory()
        self.provider = MockOAuth1Provider()

    @responses.activate
    def test_start_flow(self):
        # Request temporary credentials from provider, provide auth redirect
        responses.add(
            responses.Response(
                responses.POST,
                'http://mock1a.com/request',
                body='{"oauth_token_secret": "temp_secret", '
                       '"oauth_token": "temp_token", '
                       '"oauth_callback_confirmed": "true"}',
                status=200,
                content_type='application/json'
            )
        )

        with self.app.app.test_request_context('/oauth/connect/mock1a/'):

            # make sure the user is logged in
            authenticate(user=self.user, access_token=None, response=None)

            # auth_url is a property method - it calls out to the external
            #   service to get a temporary key and secret before returning the
            #   auth url
            url = self.provider.auth_url

            # The URL to which the user would be redirected
            assert_equal(url, 'http://mock1a.com/auth?oauth_token=temp_token')

            # Temporary credentials are added to the session
            creds = session.data['oauth_states'][self.provider.short_name]
            assert_equal(creds['token'], 'temp_token')
            assert_equal(creds['secret'], 'temp_secret')

    @responses.activate
    def test_callback(self):
        # Exchange temporary credentials for permanent credentials

        # mock a successful call to the provider to exchange temp keys for
        #   permanent keys
        responses.add(
            responses.Response(
                responses.POST,
                'http://mock1a.com/callback',
                body=(
                    'oauth_token=perm_token'
                    '&oauth_token_secret=perm_secret'
                    '&oauth_callback_confirmed=true'
                )
            )
        )

        user = UserFactory()

        # Fake a request context for the callback
        ctx = self.app.app.test_request_context(
            path='/oauth/callback/mock1a/',
            query_string='oauth_token=temp_key&oauth_verifier=mock_verifier',
        )
        with ctx:

            # make sure the user is logged in
            authenticate(user=user, access_token=None, response=None)

            session.data['oauth_states'] = {
                self.provider.short_name: {
                    'token': 'temp_key',
                    'secret': 'temp_secret',
                },
            }
            session.save()

            # do the key exchange
            self.provider.auth_callback(user=user)

        account = ExternalAccount.objects.first()
        assert_equal(account.oauth_key, 'perm_token')
        assert_equal(account.oauth_secret, 'perm_secret')
        assert_equal(account.provider_id, 'mock_provider_id')
        assert_equal(account.provider_name, 'Mock OAuth 1.0a Provider')

    @responses.activate
    def test_callback_wrong_user(self):
        # Reject temporary credentials not assigned to the user
        #
        # This prohibits users from associating their external account with
        # another user's OSF account by using XSS or similar attack vector to
        # complete the OAuth flow using the logged-in user but their own account
        # on the external service.
        #
        # If the OSF were to allow login via OAuth with the provider in question,
        # this would allow attackers to hijack OSF accounts with a simple script
        # injection.

        # mock a successful call to the provider to exchange temp keys for
        #   permanent keys
        responses.add(
            responses.Response(
                responses.POST,
                'http://mock1a.com/callback',
                body='oauth_token=perm_token'
                     '&oauth_token_secret=perm_secret'
                     '&oauth_callback_confirmed=true',
            )
        )

        user = UserFactory()
        account = ExternalAccountFactory(
            provider='mock1a',
            provider_name='Mock 1A',
            oauth_key='temp_key',
            oauth_secret='temp_secret'
        )
        account.save()
        # associate this ExternalAccount instance with the user
        user.external_accounts.add(account)
        user.save()

        malicious_user = UserFactory()

        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path='/oauth/callback/mock1a/',
                query_string='oauth_token=temp_key&oauth_verifier=mock_verifier'
        ):
            # make sure the user is logged in
            authenticate(user=malicious_user, access_token=None, response=None)

            with assert_raises(PermissionsError):
                # do the key exchange
                self.provider.auth_callback(user=malicious_user)


class TestExternalProviderOAuth2(OsfTestCase):
    # Test functionality of the ExternalProvider class, for OAuth 2.0

    def setUp(self):
        super(TestExternalProviderOAuth2, self).setUp()
        self.user = UserFactory()
        self.provider = MockOAuth2Provider()

    def test_oauth_version_default(self):
        # OAuth 2.0 is the default version
        assert_is(self.provider._oauth_version, OAUTH2)

    def test_start_flow_oauth_standard(self):
        # Generate the appropriate URL and state token - addons that follow standard OAuth protocol

        # Make sure that the mock oauth2 provider is a standard one.  The test would fail early here
        # if `test_start_flow_oauth_no_redirect()` was ran before this test and failed in the middle
        # without resetting the `ADDONS_OAUTH_NO_REDIRECT` list.
        assert self.provider.short_name not in ADDONS_OAUTH_NO_REDIRECT

        with self.app.app.test_request_context('/oauth/connect/mock2/'):

            # Make sure the user is logged in
            authenticate(user=self.user, access_token=None, response=None)

            # `auth_url` is a property method - it calls out to the external service to get a
            # temporary key and secret before returning the auth url
            url = self.provider.auth_url

            # Temporary credentials are added to the session
            creds = session.data['oauth_states'][self.provider.short_name]
            assert_in('state', creds)

            # The URL to which the user would be redirected
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # Check parameters
            expected_params = {
                'state': [creds['state']],
                'response_type': ['code'],
                'client_id': [self.provider.client_id],
                'redirect_uri': [
                    web_url_for(
                        'oauth_callback',
                        service_name=self.provider.short_name,
                        _absolute=True
                    )
                ]
            }
            assert_equal(params, expected_params)

            # Check base URL
            assert_equal(url.split('?')[0], 'https://mock2.com/auth')

    def test_start_flow_oauth_no_redirect(self):
        # Generate the appropriate URL and state token - addons that do not allow `redirect_uri`

        # Temporarily add the mock provider to the `ADDONS_OAUTH_NO_REDIRECT` list
        ADDONS_OAUTH_NO_REDIRECT.append(self.provider.short_name)

        with self.app.app.test_request_context('/oauth/connect/mock2/'):

            # Make sure the user is logged in
            authenticate(user=self.user, access_token=None, response=None)

            # `auth_url` is a property method - it calls out to the external service to get a
            # temporary key and secret before returning the auth url
            url = self.provider.auth_url

            # Temporary credentials are added to the session
            creds = session.data['oauth_states'][self.provider.short_name]
            assert_in('state', creds)

            # The URL to which the user would be redirected
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            # Check parameters - the only difference from standard OAuth flow is no `redirect_uri`.
            expected_params = {
                'state': [creds['state']],
                'response_type': ['code'],
                'client_id': [self.provider.client_id]
            }
            assert_equal(params, expected_params)

            # Check base URL
            assert_equal(url.split('?')[0], 'https://mock2.com/auth')

        # Reset the `ADDONS_OAUTH_NO_REDIRECT` list
        ADDONS_OAUTH_NO_REDIRECT.remove(self.provider.short_name)

    @mock.patch('osf.models.external.OAuth2Session')
    @mock.patch('osf.models.external.OAuth2Session.fetch_token')
    def test_callback_oauth_standard(self, mock_fetch_token, mock_oauth2session):
        # During token exchange, OAuth2Session is initialized w/ redirect_uri for standard addons.

        # Make sure that the mock oauth2 provider is a standard one.
        assert self.provider.short_name not in ADDONS_OAUTH_NO_REDIRECT

        # Mock OAuth2Session and its property `fetch_token`.
        mock_oauth2session.return_value = OAuth2Session(self.provider.client_id, None)
        mock_fetch_token.return_value = {'access_token': 'mock_access_token'}

        user = UserFactory()

        with self.app.app.test_request_context(path='/oauth/callback/mock2/',
                                               query_string='code=mock_code&state=mock_state'):
            authenticate(user=self.user, access_token=None, response=None)
            session.data['oauth_states'] = {self.provider.short_name: {'state': 'mock_state'}}
            session.save()
            self.provider.auth_callback(user=user)
            redirect_uri = web_url_for(
                'oauth_callback',
                service_name=self.provider.short_name,
                _absolute=True
            )

        mock_oauth2session.assert_called_with(self.provider.client_id, redirect_uri=redirect_uri)

    @mock.patch('osf.models.external.OAuth2Session')
    @mock.patch('osf.models.external.OAuth2Session.fetch_token')
    def test_callback_oauth_no_redirect(self, mock_fetch_token, mock_oauth2session):
        # During token exchange, OAuth2Session is initialize w/o redirect_uri for non-standard ones.

        # Temporarily add the mock provider to the `ADDONS_OAUTH_NO_REDIRECT` list.
        ADDONS_OAUTH_NO_REDIRECT.append(self.provider.short_name)

        # Mock OAuth2Session and its property `fetch_token`.
        mock_oauth2session.return_value = OAuth2Session(self.provider.client_id, None)
        mock_fetch_token.return_value = {'access_token': 'mock_access_token'}

        user = UserFactory()

        with self.app.app.test_request_context(path='/oauth/callback/mock2/',
                                               query_string='code=mock_code&state=mock_state'):
            authenticate(user=self.user, access_token=None, response=None)
            session.data['oauth_states'] = {self.provider.short_name: {'state': 'mock_state'}}
            session.save()
            self.provider.auth_callback(user=user)

        mock_oauth2session.assert_called_with(self.provider.client_id, redirect_uri=None)

        # Reset the `ADDONS_OAUTH_NO_REDIRECT` list.
        ADDONS_OAUTH_NO_REDIRECT.remove(self.provider.short_name)

    @responses.activate
    def test_callback(self):
        # Exchange temporary credentials for permanent credentials

        # Mock the exchange of the code for an access token
        _prepare_mock_oauth2_handshake_response()

        user = UserFactory()

        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path='/oauth/callback/mock2/',
                query_string='code=mock_code&state=mock_state'
        ):

            # make sure the user is logged in
            authenticate(user=self.user, access_token=None, response=None)

            session.data['oauth_states'] = {
                self.provider.short_name: {
                    'state': 'mock_state',
                },
            }
            session.save()

            # do the key exchange

            self.provider.auth_callback(user=user)

        account = ExternalAccount.objects.first()
        assert_equal(account.oauth_key, 'mock_access_token')
        assert_equal(account.provider_id, 'mock_provider_id')

    @responses.activate
    def test_provider_down(self):

        # Create a 500 error
        _prepare_mock_500_error()

        user = UserFactory()
        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path='/oauth/callback/mock2/',
                query_string='code=mock_code&state=mock_state'
        ):
            # make sure the user is logged in
            authenticate(user=user, access_token=None, response=None)

            session.data['oauth_states'] = {
                self.provider.short_name: {
                    'state': 'mock_state',
                },
            }
            session.save()

            # do the key exchange

            with assert_raises(HTTPError) as error_raised:
                self.provider.auth_callback(user=user)

            assert_equal(
                error_raised.exception.code,
                503,
            )

    @responses.activate
    def test_user_denies_access(self):

        # Create a 401 error
        _prepare_mock_401_error()

        user = UserFactory()
        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path='/oauth/callback/mock2/',
                query_string='error=mock_error&code=mock_code&state=mock_state'
        ):
            # make sure the user is logged in
            authenticate(user=user, access_token=None, response=None)

            session.data['oauth_states'] = {
                self.provider.short_name: {
                    'state': 'mock_state',
                },
            }
            session.save()

            assert_false(self.provider.auth_callback(user=user))

    @responses.activate
    def test_multiple_users_associated(self):
        # Create only one ExternalAccount for multiple OSF users
        #
        # For some providers (ex: GitHub), the act of completing the OAuth flow
        # revokes previously generated credentials. In addition, there is often no
        # way to know the user's id on the external service until after the flow
        # has completed.
        #
        # Having only one ExternalAccount instance per account on the external
        # service means that connecting subsequent OSF users to the same external
        # account will not invalidate the credentials used by the OSF for users
        # already associated.
        user_a = UserFactory()
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
        )
        user_a.external_accounts.add(external_account)
        user_a.save()

        user_b = UserFactory()

        # Mock the exchange of the code for an access token
        _prepare_mock_oauth2_handshake_response()

        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path='/oauth/callback/mock2/',
                query_string='code=mock_code&state=mock_state'
        ) as ctx:

            # make sure the user is logged in
            authenticate(user=user_b, access_token=None, response=None)

            session.data['oauth_states'] = {
                self.provider.short_name: {
                    'state': 'mock_state',
                },
            }
            session.save()

            # do the key exchange
            self.provider.auth_callback(user=user_b)

        user_a.reload()
        user_b.reload()
        external_account.reload()

        assert_equal(
            list(user_a.external_accounts.values_list('pk', flat=True)),
            list(user_b.external_accounts.values_list('pk', flat=True)),
        )

        assert_equal(
            ExternalAccount.objects.all().count(),
            1
        )

    @responses.activate
    def test_force_refresh_oauth_key(self):
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
            oauth_key='old_key',
            oauth_secret='old_secret',
            expires_at=datetime.utcfromtimestamp(time.time() - 200).replace(tzinfo=pytz.utc)
        )

        # mock a successful call to the provider to refresh tokens
        responses.add(
            responses.Response(
                responses.POST,
                self.provider.auto_refresh_url,
                body=json.dumps({
                    'access_token': 'refreshed_access_token',
                    'expires_in': 3600,
                    'refresh_token': 'refreshed_refresh_token'
                })
            )
        )

        old_expiry = external_account.expires_at
        self.provider.account = external_account
        self.provider.refresh_oauth_key(force=True)
        external_account.reload()

        assert_equal(external_account.oauth_key, 'refreshed_access_token')
        assert_equal(external_account.refresh_token, 'refreshed_refresh_token')
        assert_not_equal(external_account.expires_at, old_expiry)
        assert_true(external_account.expires_at > old_expiry)

    @responses.activate
    def test_does_need_refresh(self):
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
            oauth_key='old_key',
            oauth_secret='old_secret',
            expires_at=datetime.utcfromtimestamp(time.time() - 200).replace(tzinfo=pytz.utc),
        )

        # mock a successful call to the provider to refresh tokens
        responses.add(
            responses.Response(
                responses.POST,
                self.provider.auto_refresh_url,
                body=json.dumps({
                    'access_token': 'refreshed_access_token',
                    'expires_in': 3600,
                    'refresh_token': 'refreshed_refresh_token'
                })
            )
        )

        old_expiry = external_account.expires_at
        self.provider.account = external_account
        self.provider.refresh_oauth_key(force=False)
        external_account.reload()

        assert_equal(external_account.oauth_key, 'refreshed_access_token')
        assert_equal(external_account.refresh_token, 'refreshed_refresh_token')
        assert_not_equal(external_account.expires_at, old_expiry)
        assert_true(external_account.expires_at > old_expiry)

    @responses.activate
    def test_does_not_need_refresh(self):
        self.provider.refresh_time = 1
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
            oauth_key='old_key',
            oauth_secret='old_secret',
            refresh_token='old_refresh',
            expires_at=datetime.utcfromtimestamp(time.time() + 200).replace(tzinfo=pytz.utc),
        )

        # mock a successful call to the provider to refresh tokens
        responses.add(
            responses.Response(
                responses.POST,
                self.provider.auto_refresh_url,
                body=json.dumps({
                    'err_msg': 'Should not be hit'
                }),
                status=500
            )
        )

        # .reload() has the side effect of rounding the microsends down to 3 significant figures
        # (e.g. DT(YMDHMS, 365420) becomes DT(YMDHMS, 365000)),
        # but must occur after possible refresh to reload tokens.
        # Doing so before allows the `old_expiry == EA.expires_at` comparison to work.
        external_account.reload()
        old_expiry = external_account.expires_at
        self.provider.account = external_account
        self.provider.refresh_oauth_key(force=False)
        external_account.reload()

        assert_equal(external_account.oauth_key, 'old_key')
        assert_equal(external_account.refresh_token, 'old_refresh')
        assert_equal(external_account.expires_at, old_expiry)

    @responses.activate
    def test_refresh_oauth_key_does_not_need_refresh(self):
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
            oauth_key='old_key',
            oauth_secret='old_secret',
            expires_at=datetime.utcfromtimestamp(time.time() + 9999).replace(tzinfo=pytz.utc)
        )

        # mock a successful call to the provider to refresh tokens
        responses.add(
            responses.Response(
                responses.POST,
                self.provider.auto_refresh_url,
                body=json.dumps({
                    'err_msg': 'Should not be hit'
                }),
                status=500
            )
        )

        self.provider.account = external_account
        ret = self.provider.refresh_oauth_key(force=False)
        assert_false(ret)

    @responses.activate
    def test_refresh_with_broken_provider(self):
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
            oauth_key='old_key',
            oauth_secret='old_secret',
            expires_at=datetime.utcfromtimestamp(time.time() - 200).replace(tzinfo=pytz.utc)
        )
        self.provider.client_id = None
        self.provider.client_secret = None
        self.provider.account = external_account

        # mock a successful call to the provider to refresh tokens
        responses.add(
            responses.Response(
                responses.POST,
                self.provider.auto_refresh_url,
                body=json.dumps({
                    'err_msg': 'Should not be hit'
                }),
                status=500
            )
        )

        ret = self.provider.refresh_oauth_key(force=False)
        assert_false(ret)

    @responses.activate
    def test_refresh_without_account_or_refresh_url(self):
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
            oauth_key='old_key',
            oauth_secret='old_secret',
            expires_at=datetime.utcfromtimestamp(time.time() + 200).replace(tzinfo=pytz.utc)
        )

        # mock a successful call to the provider to refresh tokens
        responses.add(
            responses.Response(
                responses.POST,
                self.provider.auto_refresh_url,
                body=json.dumps({
                    'err_msg': 'Should not be hit'
                }),
                status=500
            )
        )

        ret = self.provider.refresh_oauth_key(force=False)
        assert_false(ret)

    @responses.activate
    def test_refresh_with_expired_credentials(self):
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
            oauth_key='old_key',
            oauth_secret='old_secret',
            expires_at=datetime.utcfromtimestamp(time.time() - 10000).replace(tzinfo=pytz.utc)  # Causes has_expired_credentials to be True
        )
        self.provider.account = external_account

        # mock a successful call to the provider to refresh tokens
        responses.add(
            responses.Response(
                responses.POST,
                self.provider.auto_refresh_url,
                body=json.dumps({
                    'err': 'Should not be hit'
                }),
                status=500
            )
        )

        ret = self.provider.refresh_oauth_key(force=False)
        assert_false(ret)

    @responses.activate
    def test_force_refresh_with_expired_credentials(self):
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
            oauth_key='old_key',
            oauth_secret='old_secret',
            expires_at=datetime.utcfromtimestamp(time.time() - 10000).replace(tzinfo=pytz.utc)  # Causes has_expired_credentials to be True
        )
        self.provider.account = external_account

        # mock a failing call to the provider to refresh tokens
        responses.add(
            responses.Response(
                responses.POST,
                self.provider.auto_refresh_url,
                body=json.dumps({
                    'error': 'invalid_grant',
                }),
                status=401
            )
        )

        with assert_raises(OAuth2Error):
            self.provider.refresh_oauth_key(force=True)
