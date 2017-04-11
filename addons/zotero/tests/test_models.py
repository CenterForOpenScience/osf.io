# -*- coding: utf-8 -*-
import pytest
import unittest

from pyzotero.zotero_errors import UserNotAuthorised

from addons.base.tests.models import (
    CitationAddonProviderTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin,
    OAuthCitationsNodeSettingsTestSuiteMixin,
)
from addons.zotero.models import (
    Zotero, NodeSettings,
)
from addons.zotero.tests.factories import (
    ZoteroAccountFactory,
    ZoteroNodeSettingsFactory,
    ZoteroUserSettingsFactory,
)
from addons.zotero.provider import ZoteroCitationsProvider

pytestmark = pytest.mark.django_db

class ZoteroProviderTestCase(CitationAddonProviderTestSuiteMixin, unittest.TestCase):

    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory
    ProviderClass = ZoteroCitationsProvider
    OAuthProviderClass = Zotero
    ApiExceptionClass = UserNotAuthorised

    def test_handle_callback(self):
        response = {
            'userID': 'Fake User ID',
            'username': 'Fake User Name',
        }

        res = self.provider.handle_callback(response)

        assert(res.get('display_name') == 'Fake User Name')
        assert(res.get('provider_id') == 'Fake User ID')


class ZoteroNodeSettingsTestCase(OAuthCitationsNodeSettingsTestSuiteMixin, unittest.TestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ProviderClass = ZoteroCitationsProvider
    OAuthProviderClass = Zotero
    ExternalAccountFactory = ZoteroAccountFactory

    NodeSettingsFactory = ZoteroNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = ZoteroUserSettingsFactory


class ZoteroUserSettingsTestCase(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory
