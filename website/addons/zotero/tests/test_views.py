# -*- coding: utf-8 -*-
import mock

import urlparse

from website.addons.base.testing import views
from website.addons.base.testing.utils import MockFolder

from website.addons.zotero.model import Zotero
from website.addons.zotero.provider import ZoteroCitationsProvider
from website.addons.zotero.serializer import ZoteroSerializer

from website.addons.zotero.tests.utils import ZoteroTestCase, mock_responses

API_URL = 'https://api.zotero.org'

class TestAuthViews(ZoteroTestCase, views.OAuthAddonAuthViewsTestCaseMixin):

    @mock.patch('website.oauth.models.OAuth1Session.fetch_request_token')
    def test_oauth_start(self, mock_token):
        mock_token.return_value = {
            'oauth_token': 'token',
            'oauth_secret': 'secret',
        }
        super(TestAuthViews, self).test_oauth_start()


class TestConfigViews(ZoteroTestCase, views.OAuthCitationAddonConfigViewsTestCaseMixin):
    folder = MockFolder()
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
