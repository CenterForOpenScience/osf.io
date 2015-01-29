import responses
from nose.tools import *

from framework.auth import authenticate
from framework.exceptions import PermissionsError
from website.oauth.models import ExternalAccount
from website.oauth.models import ExternalProvider
from website.oauth.models import OAUTH1
from website.oauth.models import OAUTH2

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


class MockOAuth2Provider(ExternalProvider):
    name = "Mock OAuth 2.0 Provider"
    short_name = "mock2"

    client_id = "mock2_client_id"
    client_secret = "mock2_client_secret"

    auth_url_base = "http://mock2.com/auth"
    callback_url = "http://mock2.com/callback"


class TestExternalProviderOAuth1(OsfTestCase):
    """Test functionality of the ExternalProvider class, for OAuth 2.0"""

    def setUp(self):
        super(TestExternalProviderOAuth1, self).setUp()
        self.provider = MockOAuth1Provider()

    def tearDown(self):
        ExternalAccount.remove()
        super(TestExternalProviderOAuth1, self).tearDown()

    @responses.activate
    def test_request_temporary_token(self):
        """Request temporary credentials from the provider"""
        responses.add(responses.POST, 'http://mock1a.com/request',
                  body='{"oauth_token_secret": "temp_secret", '
                       '"oauth_token": "temp_token", '
                       '"oauth_callback_confirmed": "true"}',
                  status=200,
                  content_type='application/json')

        # auth_url is a property method - it calls out to the external service
        #   to get a temporary key and secret before returning the auth url
        url = self.provider.auth_url

        # There should be only one external account in the DB
        account = ExternalAccount.find_one()

        # These come from the external provider, mocked here with responses.
        assert_equal(account.oauth_key, "temp_token")
        assert_equal(account.oauth_secret, "temp_secret")
        assert_equal(url, "http://mock1a.com/auth?oauth_token=temp_token")

    @responses.activate
    def test_callback(self):
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
        # associate this ExternalAccount instance with the user
        user.external_accounts.append(account)
        user.save()


        # Fake a request context for the callback
        with self.app.app.test_request_context(
                path="/oauth/callback/mock1a/",
                query_string="oauth_token=temp_key&oauth_verifier=mock_verifier"
        ) as ctx:
            # make sure the user is logged in
            authenticate(user=user, response=None)

            # do the key exchange
            self.provider.auth_callback(user=user)

        account.reload()
        assert_equal(account.oauth_key, 'perm_token')
        assert_equal(account.oauth_secret, 'perm_secret')
        assert_false(account.temporary)

    @responses.activate
    def test_callback_wrong_user(self):
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

    def test_oauth_version_default(self):
        mock = MockOAuth2Provider()
        assert_is(mock._oauth_version, OAUTH2)