from unittest import mock
import pytest

from addons.base.tests.views import OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
from addons.googledrive.tests.utils import mock_folders as sample_folder_data
from addons.googledrive.tests.utils import GoogleDriveAddonTestCase
from tests.base import OsfTestCase
from addons.googledrive.client import GoogleDriveClient
from addons.googledrive.serializer import GoogleDriveSerializer

pytestmark = pytest.mark.django_db


class TestAuthViews(GoogleDriveAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):
    pass

class TestConfigViews(GoogleDriveAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = {
        'path': 'Drive/Camera Uploads',
        'id': '1234567890'
    }
    Serializer = GoogleDriveSerializer
    client = GoogleDriveClient

    def setUp(self):
        super().setUp()
        self.mock_about = mock.patch.object(
            GoogleDriveClient,
            'about'
        )
        self.mock_about.return_value = {'rootFolderId': '24601'}
        self.mock_about.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_fetch.stop()
        super().tearDown()

    @mock.patch.object(GoogleDriveClient, 'folders')
    def test_folder_list_not_root(self, mock_drive_client_folders):
        mock_drive_client_folders.return_value = sample_folder_data['items']
        folderId = '12345'
        self.node_settings.set_auth(external_account=self.external_account, user=self.user)
        self.node_settings.save()

        url = self.project.api_url_for('googledrive_folder_list', folder_id=folderId)
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == len(sample_folder_data['items'])

    @mock.patch.object(GoogleDriveClient, 'about')
    def test_folder_list(self, mock_about):
        mock_about.return_value = {'rootFolderId': '24601'}
        super().test_folder_list()
