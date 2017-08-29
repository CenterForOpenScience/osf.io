# -*- coding: utf-8 -*-

import mock
from nose.tools import *  # noqa

from website.addons.base.testing import views
from website.addons.onedrive.client import OneDriveClient
from website.addons.onedrive.serializer import OneDriveSerializer
from website.addons.onedrive.tests.utils import OneDriveAddonTestCase
from website.addons.onedrive.tests.utils import raw_subfolder_response
from website.addons.onedrive.tests.utils import raw_root_folder_response


class TestAuthViews(OneDriveAddonTestCase, views.OAuthAddonAuthViewsTestCaseMixin):
    pass


class TestConfigViews(OneDriveAddonTestCase, views.OAuthAddonConfigViewsTestCaseMixin):
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
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), len(raw_subfolder_response))
