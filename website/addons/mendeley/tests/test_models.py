# -*- coding: utf-8 -*-
import mock

from mendeley.exception import MendeleyApiException

from tests.base import OsfTestCase
from website.addons.base.testing.models import (
    CitationAddonProviderTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin,
    OAuthCitationsNodeSettingsTestSuiteMixin,
)
from website.addons.mendeley.model import (
    Mendeley, MendeleyNodeSettings,
)
from website.addons.mendeley.provider import MendeleyCitationsProvider
from website.addons.mendeley.tests.factories import (
    MendeleyAccountFactory,
    MendeleyUserSettingsFactory,
    MendeleyNodeSettingsFactory,
)


class MendeleyProviderTestCase(CitationAddonProviderTestSuiteMixin, OsfTestCase):
    short_name = 'mendeley'
    full_name = 'Mendeley'
    ExternalAccountFactory = MendeleyAccountFactory
    ProviderClass = MendeleyCitationsProvider
    OAuthProviderClass = Mendeley
    ApiExceptionClass = MendeleyApiException

    @mock.patch('website.addons.mendeley.model.Mendeley._get_client')
    def test_handle_callback(self, mock_get_client):
        # Must return provider_id and display_name
        mock_client = mock.Mock()
        mock_client.profiles.me = mock.Mock(id='testid', display_name='testdisplay')
        mock_get_client.return_value = mock_client
        res = self.provider.handle_callback('testresponse')
        mock_get_client.assert_called_with(credentials='testresponse')
        assert(res.get('provider_id') == 'testid')
        assert(res.get('display_name') == 'testdisplay')

class MendeleyNodeSettingsTestCase(OAuthCitationsNodeSettingsTestSuiteMixin, OsfTestCase):
    short_name = 'mendeley'
    full_name = 'Mendeley'
    ExternalAccountFactory = MendeleyAccountFactory
    ProviderClass = MendeleyCitationsProvider
    OAuthProviderClass = Mendeley

    NodeSettingsFactory = MendeleyNodeSettingsFactory
    NodeSettingsClass = MendeleyNodeSettings
    UserSettingsFactory = MendeleyUserSettingsFactory

class MendeleyUserSettingsTestCase(OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):
    short_name = 'mendeley'
    full_name = 'Mendeley'
    ExternalAccountFactory = MendeleyAccountFactory
