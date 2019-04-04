# -*- coding: utf-8 -*-
import mock
import pytest
from future.moves.urllib.parse import urlparse, urljoin

from addons.base.tests import views
from addons.base.tests.utils import MockFolder

from addons.mendeley.models import Mendeley
from addons.mendeley.tests.utils import MendeleyTestCase, mock_responses
from tests.base import OsfTestCase
from addons.mendeley.provider import MendeleyCitationsProvider
from addons.mendeley.serializer import MendeleySerializer


API_URL = 'https://api.mendeley.com'
pytestmark = pytest.mark.django_db

class TestAuthViews(MendeleyTestCase, views.OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):
    pass

class TestConfigViews(MendeleyTestCase, views.OAuthCitationAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = MockFolder()
    Serializer = MendeleySerializer
    client = Mendeley
    citationsProvider = MendeleyCitationsProvider
    foldersApiUrl = urljoin(API_URL, 'folders')
    documentsApiUrl = urljoin(API_URL, 'documents')
    mockResponses = mock_responses

    @mock.patch('addons.mendeley.models.NodeSettings._fetch_folder_name', mock.PropertyMock(return_value='Fake Name'))
    def test_deauthorize_node(self):
        super(TestConfigViews, self).test_deauthorize_node()
