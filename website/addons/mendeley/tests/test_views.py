# -*- coding: utf-8 -*-
import mock

import urlparse

from website.addons.base.testing import views
from website.addons.base.testing.utils import MockFolder

from website.addons.mendeley.model import Mendeley
from website.addons.mendeley.provider import MendeleyCitationsProvider
from website.addons.mendeley.serializer import MendeleySerializer

from website.addons.mendeley.tests.utils import MendeleyTestCase, mock_responses

API_URL = 'https://api.mendeley.com'

class TestAuthViews(MendeleyTestCase, views.OAuthAddonAuthViewsTestCaseMixin):
    pass

class TestConfigViews(MendeleyTestCase, views.OAuthCitationAddonConfigViewsTestCaseMixin):
    folder = MockFolder()
    Serializer = MendeleySerializer
    client = Mendeley
    citationsProvider = MendeleyCitationsProvider
    foldersApiUrl = urlparse.urljoin(API_URL, 'folders')
    documentsApiUrl = urlparse.urljoin(API_URL, 'documents')
    mockResponses = mock_responses

    @mock.patch('website.addons.mendeley.model.MendeleyNodeSettings._fetch_folder_name', mock.PropertyMock(return_value='Fake Name'))
    def test_deauthorize_node(self):
        super(TestConfigViews, self).test_deauthorize_node()
