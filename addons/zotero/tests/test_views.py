from unittest import mock
import pytest
from urllib.parse import urlparse, urljoin
import responses

from framework.auth import Auth
from addons.base.tests import views
from addons.base.tests.utils import MockLibrary, MockFolder
from addons.zotero.models import Zotero
from addons.zotero.provider import ZoteroCitationsProvider
from addons.zotero.serializer import ZoteroSerializer

from addons.zotero.tests.utils import ZoteroTestCase, mock_responses, mock_responses_with_filed_and_unfiled
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
        super().test_oauth_start()


class TestConfigViews(ZoteroTestCase, views.OAuthCitationAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = MockFolder()
    library = MockLibrary()
    Serializer = ZoteroSerializer
    client = Zotero
    citationsProvider = ZoteroCitationsProvider
    foldersApiUrl = None
    documentsApiUrl = None
    mockResponses = mock_responses
    mockResponsesFiledUnfiled = mock_responses_with_filed_and_unfiled

    def setUp(self):
        super().setUp()
        self.foldersApiUrl = urljoin(API_URL, 'users/{}/collections'
            .format(self.external_account.provider_id))
        self.documentsApiUrl = urljoin(API_URL, 'users/{}/items/top'
            .format(self.external_account.provider_id))

        # Sets library key
        self.citationsProvider().set_config(
            self.node_settings,
            self.user,
            self.folder.json['id'],
            self.folder.name,
            Auth(self.user),
            'personal',
            'personal'
        )

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
        assert not self.node_settings.complete
        assert self.node_settings.list_id == None
        assert self.node_settings.library_id == 'Fake Library Key'
        res = self.citationsProvider().widget(self.project.get_addon(self.ADDON_SHORT_NAME))
        assert not res['complete']
        assert res['list_id'] == None
        assert res['library_id'] == 'Fake Library Key'

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
        assert self.node_settings.complete
        assert self.node_settings.list_id == 'Fake Key'
        assert self.node_settings.library_id == 'Fake Library Key'
        res = self.citationsProvider().widget(self.project.get_addon(self.ADDON_SHORT_NAME))
        assert res['complete']
        assert res['list_id'] == 'Fake Key'
        assert res['library_id'] == 'Fake Library Key'

    @responses.activate
    def test_citation_list_root_only_unfiled_items_included(self):
        responses.add(
            responses.Response(
                responses.GET,
                self.foldersApiUrl,
                body=self.mockResponsesFiledUnfiled['folders'],
                content_type='application/json'
            )
        )

        responses.add(
            responses.Response(
                responses.GET,
                self.documentsApiUrl,
                body=self.mockResponsesFiledUnfiled['documents'],
                content_type='application/json'
            )
        )

        res = self.app.get(
            self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_citation_list', list_id='ROOT'),
            auth=self.user.auth
        )

        children = res.json['contents']
        # There are three items, one folder and two files, but one of the files gets pulled out because it
        # belongs to a collection
        assert len(children) == 2
        assert children[0]['kind'] == 'folder'
        assert children[1]['kind'] == 'file'
        assert children[1].get('csl') is not None
