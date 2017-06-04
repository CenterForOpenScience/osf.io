# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa

from website.addons.base.testing import views
from website.addons.googledrive.client import GoogleDriveClient
from website.addons.googledrive.serializer import GoogleDriveSerializer
from website.addons.googledrive.tests.utils import mock_folders as sample_folder_data
from website.addons.googledrive.tests.utils import GoogleDriveAddonTestCase


class TestAuthViews(GoogleDriveAddonTestCase, views.OAuthAddonAuthViewsTestCaseMixin):
    pass

class TestConfigViews(GoogleDriveAddonTestCase, views.OAuthAddonConfigViewsTestCaseMixin):
    folder = {
        'path': 'Drive/Camera Uploads',
        'id': '1234567890'
    }
    Serializer = GoogleDriveSerializer
    client = GoogleDriveClient

    def setUp(self):
        super(TestConfigViews, self).setUp()
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
        super(TestConfigViews, self).tearDown()

    @mock.patch.object(GoogleDriveClient, 'folders')
    def test_folder_list_not_root(self, mock_drive_client_folders):
        mock_drive_client_folders.return_value = sample_folder_data['items']
        folderId = '12345'
        self.node_settings.set_auth(external_account=self.external_account, user=self.user)
        self.node_settings.save()

        url = self.project.api_url_for('googledrive_folder_list', folder_id=folderId)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), len(sample_folder_data['items']))

    @mock.patch.object(GoogleDriveClient, 'about')
    def test_folder_list(self, mock_about):
        mock_about.return_value = {'rootFolderId': '24601'}
        super(TestConfigViews, self).test_folder_list()
