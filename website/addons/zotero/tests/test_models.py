# -*- coding: utf-8 -*-

import mock
from nose.tools import *  # noqa

from framework.auth.core import Auth
from framework.exceptions import PermissionsError

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.base.testing import models
from website.addons.zotero.tests.factories import (
    ZoteroAccountFactory,
    ZoteroUserSettingsFactory,
    ZoteroNodeSettingsFactory,
)
from website.addons.zotero.provider import ZoteroCitationsProvider

from pyzotero.zotero_errors import UserNotAuthorised
from framework.exceptions import HTTPError

from website.addons.zotero import model


class ZoteroProviderTestCase(models.CitationAddonProviderTestSuiteMixin, OsfTestCase):

    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory
    ProviderClass = ZoteroCitationsProvider
    OAuthProviderClass = model.Zotero
    ApiExceptionClass = UserNotAuthorised

    def test_handle_callback(self):
        mock_response = {
            'userID': 'Fake User ID',
            'username': 'Fake User Name',
        }

        res = self.provider.handle_callback(mock_response)

        assert_equal(res.get('display_name'), 'Fake User Name')
        assert_equal(res.get('provider_id'), 'Fake User ID')


class ZoteroNodeSettingsTestCase(models.OAuthCitationsNodeSettingsTestSuiteMixin, OsfTestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ProviderClass = ZoteroCitationsProvider
    OAuthProviderClass = model.Zotero
    ExternalAccountFactory = ZoteroAccountFactory

    NodeSettingsFactory = ZoteroNodeSettingsFactory
    NodeSettingsClass = model.ZoteroNodeSettings
    UserSettingsFactory = ZoteroUserSettingsFactory


class ZoteroUserSettingsTestCase(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory
