# -*- coding: utf-8 -*-
import mock
import pytest
import urlparse
from framework.auth import Auth
from nose.tools import (assert_equal, assert_true, assert_false)
from addons.base.tests import views
from addons.base.tests.utils import MockLibrary, MockFolder
from addons.zotero.models import Zotero
from addons.zotero.provider import ZoteroCitationsProvider
from addons.zotero.serializer import ZoteroSerializer

from addons.zotero.tests.utils import ZoteroTestCase, mock_responses
from tests.base import OsfTestCase

API_URL = 'https://api.zotero.org'
pytestmark = pytest.mark.django_db

class TestAuthViews(ZoteroTestCase, views.OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    @mock.patch('osf.models.external.OAuth1Session.fetch_request_token')
    def test_oauth_start(self, mock_token):
        mock_token.return_value = {
            'oauth_token': 'token',
            'oauth_secret': 'secret',
        }
        super(TestAuthViews, self).test_oauth_start()


class TestConfigViews(ZoteroTestCase, views.OAuthCitationAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = MockFolder()
    library = MockLibrary()
    Serializer = ZoteroSerializer
    client = Zotero
    citationsProvider = ZoteroCitationsProvider
    foldersApiUrl = None
    documentsApiUrl = None
    mockResponses = mock_responses

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.foldersApiUrl = urlparse.urljoin(API_URL, 'users/{}/collections'
            .format(self.external_account.provider_id))
        self.documentsApiUrl = urlparse.urljoin(API_URL, 'users/{}/items'
            .format(self.external_account.provider_id))

    def test_widget_view_incomplete_library_set_only(self):
        # JSON: everything a widget needs
        # When library is set in zotero, folder is cleared.
        self.citationsProvider().set_config(
            self.node_settings,
            self.user,
            self.folder.json['id'],
            self.folder.name,
            Auth(self.user),
            self.library.json['id'],
            self.library.name
        )
        assert_false(self.node_settings.complete)
        assert_equal(self.node_settings.list_id, None)
        assert_equal(self.node_settings.library_id, 'Fake Library Key')
        res = self.citationsProvider().widget(self.project.get_addon(self.ADDON_SHORT_NAME))
        assert_false(res['complete'])
        assert_equal(res['list_id'], None)
        assert_equal(res['library_id'], 'Fake Library Key')

    def test_widget_view_complete(self):
        # JSON: everything a widget needs
        # Library must be set, then folder.
        # Sets library key
        self.citationsProvider().set_config(
            self.node_settings,
            self.user,
            self.folder.json['id'],
            self.folder.name,
            Auth(self.user),
            self.library.json['id'],
            self.library.name
        )
        # Sets folder
        self.citationsProvider().set_config(
            self.node_settings,
            self.user,
            self.folder.json['id'],
            self.folder.name,
            Auth(self.user),
        )
        assert_true(self.node_settings.complete)
        assert_equal(self.node_settings.list_id, 'Fake Key')
        assert_equal(self.node_settings.library_id, 'Fake Library Key')
        res = self.citationsProvider().widget(self.project.get_addon(self.ADDON_SHORT_NAME))
        assert_true(res['complete'])
        assert_equal(res['list_id'], 'Fake Key')
        assert_equal(res['library_id'], 'Fake Library Key')
