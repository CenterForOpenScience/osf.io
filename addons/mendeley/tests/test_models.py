# -*- coding: utf-8 -*-
import mock
import pytest
import unittest

from mendeley.exception import MendeleyApiException

from addons.base.tests.models import (
    CitationAddonProviderTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin,
    OAuthCitationsNodeSettingsTestSuiteMixin,
)
from addons.mendeley.models import (
    Mendeley, NodeSettings,
)
from addons.mendeley.provider import MendeleyCitationsProvider
from addons.mendeley.tests.factories import (
    MendeleyAccountFactory,
    MendeleyUserSettingsFactory,
    MendeleyNodeSettingsFactory,
)

pytestmark = pytest.mark.django_db

class MendeleyProviderTestCase(CitationAddonProviderTestSuiteMixin, unittest.TestCase):
    short_name = 'mendeley'
    full_name = 'Mendeley'
    ExternalAccountFactory = MendeleyAccountFactory
    ProviderClass = MendeleyCitationsProvider
    OAuthProviderClass = Mendeley
    ApiExceptionClass = MendeleyApiException

    @mock.patch('addons.mendeley.models.Mendeley._get_client')
    def test_handle_callback(self, mock_get_client):
        # Must return provider_id and display_name
        mock_client = mock.Mock()
        mock_client.profiles.me = mock.Mock(id='testid', display_name='testdisplay')
        mock_get_client.return_value = mock_client
        res = self.provider.handle_callback('testresponse')
        mock_get_client.assert_called_with(credentials='testresponse')
        assert(res.get('provider_id') == 'testid')
        assert(res.get('display_name') == 'testdisplay')

class MendeleyNodeSettingsTestCase(OAuthCitationsNodeSettingsTestSuiteMixin, unittest.TestCase):
    short_name = 'mendeley'
    full_name = 'Mendeley'
    ExternalAccountFactory = MendeleyAccountFactory
    ProviderClass = MendeleyCitationsProvider
    OAuthProviderClass = Mendeley

    NodeSettingsFactory = MendeleyNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = MendeleyUserSettingsFactory

class MendeleyUserSettingsTestCase(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    short_name = 'mendeley'
    full_name = 'Mendeley'
    ExternalAccountFactory = MendeleyAccountFactory
