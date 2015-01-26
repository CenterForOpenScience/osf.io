from nose.tools import *

from website.oauth.models import ExternalProvider
from website.oauth.models import OAUTH1
from website.oauth.models import OAUTH2

from tests.base import OsfTestCase


class MockOauth2Provider(ExternalProvider):
    name = "Mock OAuth 2.0 Provider"
    short_name = "mock2"

    client_id = 'mock2_client_id'
    client_secret = 'mock2_client_secret'

    auth_url_base = 'http://mock2.com/auth'
    callback_url = 'http://mock2.com/callback'

    def handle_callback(self, data):
        pass


class TestExternalProvider(OsfTestCase):
    def test_instantiate(self):
        mock = MockOauth2Provider()

    def test_oauth_version_default(self):
        mock = MockOauth2Provider()
        assert_is(mock._oauth_version, OAUTH2)