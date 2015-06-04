import httplib as http
import logging
import json
import time
import urlparse

import httpretty
from nose.tools import *  # noqa

from framework.auth import authenticate
from framework.exceptions import PermissionsError, HTTPError
from framework.sessions import get_session
from website.oauth.models import (
    ExternalAccount,
    ExternalProvider,
    OAUTH1,
    OAUTH2,
)
from website.util import api_url_for, web_url_for

from tests.base import OsfTestCase
from tests.factories import (
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
    name = "Mock OAuth 1.0a Provider"
    short_name = "mock1a"

    client_id = "mock1a_client_id"
    client_secret = "mock1a_client_secret"

    auth_url_base = "http://mock1a.com/auth"
    request_token_url = "http://mock1a.com/request"
    callback_url = "http://mock1a.com/callback"

    def handle_callback(self, response):
        return {
            'provider_id': 'mock_provider_id'
        }


def _prepare_mock_oauth2_handshake_response(expires_in=3600):

    httpretty.register_uri(
        httpretty.POST,
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

def _prepare_mock_500_error():
    httpretty.register_uri(
        httpretty.POST,
        'https://mock2.com/callback',
        body='{"error": "not found"}',
        status=503,
        content_type='application/json',
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

    def tearDown(self):
        ExternalAccount._clear_caches()
        ExternalAccount.remove()
        self.user.remove()
        super(TestExternalAccount, self).tearDown()

    def test_disconnect(self):
        # Disconnect an external account from a user
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
        )
        self.user.external_accounts.append(external_account)
        self.user.save()

        # If the external account isn't attached, this test has no meaning
        assert_equal(ExternalAccount.find().count(), 1)
        assert_in(
            external_account,
            self.user.external_accounts,
        )

        response = self.app.delete(
            api_url_for('oauth_disconnect',
                        external_account_id=external_account._id),
            auth=self.user.auth
        )

        # Request succeeded
        assert_equal(
            response.status_code,
            http.OK,
        )

        self.user.reload()
        # external_account.reload()

        # External account has been disassociated with the user
        assert_not_in(
            external_account,
            self.user.external_accounts,
        )

        # External account is still in the database
        assert_equal(ExternalAccount.find().count(), 1)

    def test_disconnect_with_multiple_connected(self):
        # Disconnect an account connected to multiple users from one user
        external_account = ExternalAccountFactory(
            provider='mock2',
            provider_id='mock_provider_id',
            provider_name='Mock Provider',
        )
        self.user.external_accounts.append(external_account)
        self.user.save()

        other_user = UserFactory()
        other_user.external_accounts.append(external_account)
        other_user.save()

        response = self.app.delete(
            api_url_for('oauth_disconnect',
                        external_account_id=external_account._id),
            auth=self.user.auth
        )

        # Request succeeded
        assert_equal(
            response.status_code,
            http.OK,
        )

        self.user.reload()

        # External account has been disassociated with the user
        assert_not_in(
            external_account,
            self.user.external_accounts,
        )

        # External account is still in the database
        assert_equal(ExternalAccount.find().count(), 1)

        other_user.reload()

        # External account is still associated with the other user
        assert_in(
            external_account,
            other_user.external_accounts,
        )


class TestExternalProviderOAuth1(OsfTestCase):
    # Test functionality of the ExternalProvider class, for OAuth 1.0a

    def setUp(self):
        super(TestExternalProviderOAuth1, self).setUp()
        self.user = UserFactory()
        self.provider = MockOAuth1Provider()

    def tearDown(self):
        ExternalAccount.remove()
        self.user.remove()
        super(TestExternalProviderOAuth1, self).tearDown()

    @httpretty.activate
    def test_start_flow(self):
        # Request temporary credentials from provider, provide auth redirect
        httpretty.register_uri(httpretty.POST, 'http://mock1a.com/request',
                  body='{"oauth_token_secret": "temp_secret", '
                       '"oauth_token": "temp_token", '
                       '"oauth_callback_confirmed": "true"}',
                  status=200,
                  content_type='application/json')

        with self.app.app.test_request_context('/oauth/connect/mock1a/'):

            # make sure the user is logged in
            authenticate(user=self.user, access_token=None, response=None)

            # auth_url is a property method - it calls out to the external
            #   service to get a temporary key and secret before returning the
            #   auth url
            url = self.provider.auth_url

            # The URL to which the user would be redirected
            assert_equal(url, "http://mock1a.com/auth?oauth_token=temp_token")

            session = get_session()

            # Temporary credentials are added to the session
            creds = session.data['oauth_states'][self.provider.short_name]
            assert_equal(creds['token'], 'temp_token')
            assert_equal(creds['secret'], 'temp_secret')

    @httpretty.activate
    def test_callback(self):
        # Exchange temporary credentials for permanent credentials

        # mock a successful call to the provider to exchange temp keys for
        #   permanent keys
        httpretty.register_uri(
            httpretty.POST,
            'http://mock1a.com/callback',
            body=(
                'oauth_token=perm_token'
                '&oauth_token_secret=perm_secret'
                '&oauth_callback_confirmed=true'
            ),
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

            session = get_session()
            session.data['oauth_states'] = {
                self.provider.short_name: {
                    'token': 'temp_key',
                    'secret': 'temp_secret',
                },
            }
            session.save()

            # do the key exchange
            self.provider.auth_callback(user=user)

        account = ExternalAccount.find_one()
        assert_equal(account.oauth_key, 'perm_token')
        assert_equal(account.oauth_secret, 'perm_secret')
        assert_equal(account.provider_id, 'mock_provider_id')
        assert_equal(account.provider_name, 'Mock OAuth 1.0a Provider')

    @httpretty.activate
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
        httpretty.register_uri(
            httpretty.POST,
            'http://mock1a.com/callback',
             body='oauth_token=perm_token'
                  '&oauth_token_secret=perm_secret'
                  '&oauth_callback_confirmed=true',
        )

        user = UserFactory()
        account = ExternalAccountFactory(
            provider="mock1a",
            provider_name='Mock 1A',
            oauth_key="temp_key",
            oauth_secret="temp_secret",
            temporary=True
        )
        account.save()
        # associate this ExternalAccount instance with the user
        user.external_accounts.append(account)
        user.save()

        malicious_user = UserFactory()

        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path="/oauth/callback/mock1a/",
                query_string="oauth_token=temp_key&oauth_verifier=mock_verifier"
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

    def tearDown(self):
        ExternalAccount._clear_caches()
        ExternalAccount.remove()
        self.user.remove()
        super(TestExternalProviderOAuth2, self).tearDown()

    def test_oauth_version_default(self):
        # OAuth 2.0 is the default version
        assert_is(self.provider._oauth_version, OAUTH2)

    def test_start_flow(self):
        # Generate the appropriate URL and state token

        with self.app.app.test_request_context("/oauth/connect/mock2/"):

            # make sure the user is logged in
            authenticate(user=self.user, access_token=None, response=None)

            # auth_url is a property method - it calls out to the external
            #   service to get a temporary key and secret before returning the
            #   auth url
            url = self.provider.auth_url

            session = get_session()

            # Temporary credentials are added to the session
            creds = session.data['oauth_states'][self.provider.short_name]
            assert_in('state', creds)

            # The URL to which the user would be redirected
            parsed = urlparse.urlparse(url)
            params = urlparse.parse_qs(parsed.query)

            # check parameters
            assert_equal(
                params,
                {
                    'state': [creds['state']],
                    'response_type': ['code'],
                    'client_id': [self.provider.client_id],
                    'redirect_uri': [
                        web_url_for('oauth_callback',
                                    service_name=self.provider.short_name,
                                    _absolute=True)
                    ]
                }
            )

            # check base URL
            assert_equal(
                url.split("?")[0],
                "https://mock2.com/auth",
            )

    @httpretty.activate
    def test_callback(self):
        # Exchange temporary credentials for permanent credentials

        # Mock the exchange of the code for an access token
        _prepare_mock_oauth2_handshake_response()

        user = UserFactory()

        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path="/oauth/callback/mock2/",
                query_string="code=mock_code&state=mock_state"
        ):

            # make sure the user is logged in
            authenticate(user=self.user, access_token=None, response=None)

            session = get_session()
            session.data['oauth_states'] = {
                self.provider.short_name: {
                    'state': 'mock_state',
                },
            }
            session.save()

            # do the key exchange

            self.provider.auth_callback(user=user)

        account = ExternalAccount.find_one()
        assert_equal(account.oauth_key, 'mock_access_token')
        assert_equal(account.provider_id, 'mock_provider_id')

    @httpretty.activate
    def test_provider_down(self):

        # Create a 500 error
        _prepare_mock_500_error()

        user = UserFactory()
        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path="/oauth/callback/mock2/",
                query_string="code=mock_code&state=mock_state"
        ):
            # make sure the user is logged in
            authenticate(user=user, access_token=None, response=None)

            session = get_session()
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

    @httpretty.activate
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
        user_a.external_accounts.append(external_account)
        user_a.save()

        user_b = UserFactory()

        # Mock the exchange of the code for an access token
        _prepare_mock_oauth2_handshake_response()

        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path="/oauth/callback/mock2/",
                query_string="code=mock_code&state=mock_state"
        ) as ctx:

            # make sure the user is logged in
            authenticate(user=user_b, access_token=None, response=None)

            session = get_session()
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
            user_a.external_accounts,
            user_b.external_accounts,
        )

        assert_equal(
            ExternalAccount.find().count(),
            1
        )
