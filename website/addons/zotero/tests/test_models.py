# -*- coding: utf-8 -*-

from pyzotero.zotero_errors import UserNotAuthorised

from tests.base import OsfTestCase
from website.addons.base.testing.models import (
    CitationAddonProviderTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin,
    OAuthCitationsNodeSettingsTestSuiteMixin,
)
from website.addons.zotero.model import (
    Zotero, ZoteroNodeSettings,
)
from website.addons.zotero.provider import ZoteroCitationsProvider
from website.addons.zotero.tests.factories import (
    ZoteroAccountFactory,
    ZoteroNodeSettingsFactory,
    ZoteroUserSettingsFactory,
)


class ZoteroProviderTestCase(CitationAddonProviderTestSuiteMixin, OsfTestCase):

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


class ZoteroNodeSettingsTestCase(OAuthCitationsNodeSettingsTestSuiteMixin, OsfTestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ProviderClass = ZoteroCitationsProvider
    OAuthProviderClass = Zotero
    ExternalAccountFactory = ZoteroAccountFactory

    NodeSettingsFactory = ZoteroNodeSettingsFactory
    NodeSettingsClass = ZoteroNodeSettings
    UserSettingsFactory = ZoteroUserSettingsFactory


class ZoteroUserSettingsTestCase(OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory
