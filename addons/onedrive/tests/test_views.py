# -*- coding: utf-8 -*-
import mock
import pytest

from addons.base.tests import views
from addons.onedrive.client import OneDriveClient
from addons.onedrive.serializer import OneDriveSerializer
from addons.onedrive.tests.utils import OneDriveAddonTestCase, raw_subfolder_response, raw_root_folder_response
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestAuthViews(OneDriveAddonTestCase, views.OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):
    pass


class TestConfigViews(OneDriveAddonTestCase, views.OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = {
        'path': 'Drive/Camera Uploads',
        'id': '1234567890'
    }
    Serializer = OneDriveSerializer
    client = OneDriveClient

    def setUp(self):
        super(TestConfigViews, self).setUp()

        self.mock_folders = mock.patch.object(OneDriveClient, 'folders')
        self.mock_folders.return_value = raw_root_folder_response
        self.mock_folders.start()

        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_folders.stop()
        self.mock_fetch.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch.object(OneDriveClient, 'folders')
    def test_folder_list_not_root(self, mock_drive_client_folders):
        mock_drive_client_folders.return_value = raw_subfolder_response

        self.node_settings.set_auth(external_account=self.external_account, user=self.user)
        self.node_settings.save()

        folderId = '12345'
        url = self.project.api_url_for('onedrive_folder_list', folder_id=folderId)
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == len(raw_subfolder_response)
