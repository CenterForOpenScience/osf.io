# -*- coding: utf-8 -*-

import mock
from nose.tools import *  # noqa

from framework.auth.core import Auth
from framework.exceptions import PermissionsError

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.base.testing import models
from website.addons.mendeley.tests.factories import (
    MendeleyAccountFactory,
    MendeleyUserSettingsFactory,
    MendeleyNodeSettingsFactory,
)
from website.addons.mendeley.provider import MendeleyCitationsProvider

import datetime

from mendeley.exception import MendeleyApiException
from framework.exceptions import HTTPError

from website.addons.mendeley import model


class MockFolder(object):

    @property
    def name(self):
        return 'somename'

    @property
    def json(self):
        return {'id': 'abc123', 'parent_id': 'cba321'}


class MendeleyProviderTestCase(OsfTestCase):

    def setUp(self):
        super(MendeleyProviderTestCase, self).setUp()
        self.provider = model.Mendeley()

    @mock.patch('website.addons.mendeley.model.Mendeley._get_client')
    def test_handle_callback(self, mock_get_client):
        # Must return provider_id and display_name
        mock_client = mock.Mock()
        mock_client.profiles.me = mock.Mock(id='testid', display_name='testdisplay')
        mock_get_client.return_value = mock_client
        res = self.provider.handle_callback('testresponse')
        mock_get_client.assert_called_with('testresponse')
        assert_equal(res.get('provider_id'), 'testid')
        assert_equal(res.get('display_name'), 'testdisplay')

    @mock.patch('website.addons.mendeley.model.Mendeley._get_client')
    def test_client_not_cached(self, mock_get_client):
        # The first call to .client returns a new client
        mock_account = mock.Mock()
        mock_account.expires_at = datetime.datetime.now()
        self.provider.account = mock_account
        self.provider.client
        mock_get_client.assert_called
        assert_true(mock_get_client.called)

    @mock.patch('website.addons.mendeley.model.Mendeley._get_client')
    def test_client_cached(self, mock_get_client):
        # Repeated calls to .client returns the same client
        self.provider._client = mock.Mock()
        res = self.provider.client
        assert_equal(res, self.provider._client)
        assert_false(mock_get_client.called)

    def test_citation_lists(self):
        mock_client = mock.Mock()
        mock_folders = [MockFolder()]
        mock_list = mock.Mock()
        mock_list.items = mock_folders
        mock_client.folders.list.return_value = mock_list
        self.provider._client = mock_client
        mock_account = mock.Mock()
        self.provider.account = mock_account
        res = self.provider.citation_lists(MendeleyCitationsProvider()._extract_folder)
        assert_equal(res[1]['name'], mock_folders[0].name)
        assert_equal(res[1]['id'], mock_folders[0].json['id'])

    def test_mendeley_has_access(self):
        mock_client = mock.Mock()
        mock_client.folders.list.return_value = MendeleyApiException({'status_code': 403, 'text': 'Mocked 403 MendeleyApiException'})
        self.provider._client = mock_client
        res = self.provider._client
        assert_raises(HTTPError(403))

class MendeleyNodeSettingsTestCase(models.OAuthCitationsNodeSettingsTestSuiteMixin, OsfTestCase):
    short_name = 'mendeley'
    full_name = 'Mendeley'
    ProviderClass = MendeleyCitationsProvider
    OAuthProviderClass = model.Mendeley
    ExternalAccountFactory = MendeleyAccountFactory

    NodeSettingsFactory = MendeleyNodeSettingsFactory
    NodeSettingsClass = model.MendeleyNodeSettings
    UserSettingsFactory = MendeleyUserSettingsFactory

class MendeleyUserSettingsTestCase(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):
    short_name = 'mendeley'
    full_name = 'Mendeley'
    ExternalAccountFactory = MendeleyAccountFactory
