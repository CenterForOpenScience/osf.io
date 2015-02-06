import responses
import urlparse
from nose.tools import *


from framework.auth import authenticate
from framework.exceptions import PermissionsError
from framework.sessions import get_session
from website.oauth.models import ExternalAccount
from website.oauth.models import ExternalProvider
from website.oauth.models import OAUTH1
from website.oauth.models import OAUTH2
from website.util import web_url_for

from tests.base import OsfTestCase
from tests.factories import ExternalAccountFactory
from tests.factories import UserFactory


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


class MockOAuth2Provider(ExternalProvider):
    name = "Mock OAuth 2.0 Provider"
    short_name = "mock2"

    client_id = "mock2_client_id"
    client_secret = "mock2_client_secret"

    auth_url_base = "https://mock2.com/auth"
    callback_url = "https://mock2.com/callback"

    def handle_callback(self, response):
        return {
            'provider_id': 'mock_provider_id'
        }


class TestExternalProviderOAuth1(OsfTestCase):
    """Test functionality of the ExternalProvider class, for OAuth 1.0a"""

    def setUp(self):
        super(TestExternalProviderOAuth1, self).setUp()
        self.user = UserFactory()
        self.provider = MockOAuth1Provider()

    def tearDown(self):
        ExternalAccount.remove()
        self.user.remove()
        super(TestExternalProviderOAuth1, self).tearDown()

    @responses.activate
    def test_start_flow(self):
        """Request temporary credentials from the provider"""
        responses.add(responses.POST, 'http://mock1a.com/request',
                  body='{"oauth_token_secret": "temp_secret", '
                       '"oauth_token": "temp_token", '
                       '"oauth_callback_confirmed": "true"}',
                  status=200,
                  content_type='application/json')

        with self.app.app.test_request_context("/oauth/connect/mock1a/") as ctx:

            # make sure the user is logged in
            authenticate(user=self.user, response=None)

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


    @responses.activate
    def test_callback(self):
        """Exchange temporary credentials for permanent credentials"""

        # mock a successful call to the provider to exchange temp keys for
        #   permanent keys
        responses.add(
            responses.POST,
            'http://mock1a.com/callback',
             body='oauth_token=perm_token'
                  '&oauth_token_secret=perm_secret'
                  '&oauth_callback_confirmed=true',
        )

        user = UserFactory()

        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path="/oauth/callback/mock1a/",
                query_string="oauth_token=temp_key&oauth_verifier=mock_verifier"
        ) as ctx:

            # make sure the user is logged in
            authenticate(user=user, response=None)

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


    @responses.activate
    def test_callback_wrong_user(self):
        """Do not accept temporary credentials not assigned to the user"""

        # mock a successful call to the provider to exchange temp keys for
        #   permanent keys
        responses.add(
            responses.POST,
            'http://mock1a.com/callback',
             body='oauth_token=perm_token'
                  '&oauth_token_secret=perm_secret'
                  '&oauth_callback_confirmed=true',
        )

        user = UserFactory()
        account = ExternalAccountFactory(
            provider="mock1a",
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
        ) as ctx:
            # make sure the user is logged in
            authenticate(user=malicious_user, response=None)

            with assert_raises(PermissionsError):
                # do the key exchange
                self.provider.auth_callback(user=malicious_user)


class TestExternalProviderOAuth2(OsfTestCase):
    """Test functionality of the ExternalProvider class, for OAuth 2.0"""

    def setUp(self):
        super(TestExternalProviderOAuth2, self).setUp()
        self.user = UserFactory()
        self.provider = MockOAuth2Provider()

    def tearDown(self):
        ExternalAccount.remove()
        self.user.remove()
        super(TestExternalProviderOAuth2, self).tearDown()

    def test_oauth_version_default(self):
        """OAuth 2.0 is the default version"""
        assert_is(self.provider._oauth_version, OAUTH2)

    def test_start_flow(self):
        """Generate the appropriate URL and state token"""

        with self.app.app.test_request_context("/oauth/connect/mock2/") as ctx:

            # make sure the user is logged in
            authenticate(user=self.user, response=None)

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
                    'redirect_uri':[
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

        def test_multiple_users_associated(self):
            """Only one ExternalAccount is created for multiple OSF users"""
            assert_true(False)

        def test_multiple_users_disconnect(self):
            """One users removes ExternalAccount, other users still attached"""
            assert_true(False)