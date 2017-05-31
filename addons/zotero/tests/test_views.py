# -*- coding: utf-8 -*-
import mock
import pytest
import urlparse

from addons.base.tests import views
from addons.base.tests.utils import MockFolder

from addons.zotero.models import Zotero
from addons.zotero.provider import ZoteroCitationsProvider
from addons.zotero.serializer import ZoteroSerializer

from addons.zotero.tests.utils import ZoteroTestCase, mock_responses
from tests.base import OsfTestCase

API_URL = 'https://api.zotero.org'
pytestmark = pytest.mark.django_db

class TestAuthViews(ZoteroTestCase, views.OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    @mock.patch('website.oauth.models.OAuth1Session.fetch_request_token')
    def test_oauth_start(self, mock_token):
        mock_token.return_value = {
            'oauth_token': 'token',
            'oauth_secret': 'secret',
        }
        super(TestAuthViews, self).test_oauth_start()


class TestConfigViews(ZoteroTestCase, views.OAuthCitationAddonConfigViewsTestCaseMixin, OsfTestCase):
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
