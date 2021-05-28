# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa
import pytest

from addons.base.tests.views import OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
from addons.googledriveinstitutions.tests.utils import mock_folders as sample_folder_data
from addons.googledriveinstitutions.tests.utils import GoogleDriveInstitutionsAddonTestCase
from tests.base import OsfTestCase
from osf_tests.factories import InstitutionFactory
from addons.googledriveinstitutions.client import GoogleDriveInstitutionsClient
from addons.googledriveinstitutions.serializer import GoogleDriveInstitutionsSerializer
from admin.rdm_addons.utils import get_rdm_addon_option

pytestmark = pytest.mark.django_db


class TestAuthViews(GoogleDriveInstitutionsAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    def test_oauth_start(self):
        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        self.user.save()
        rdm_addon_option = get_rdm_addon_option(institution.id, self.ADDON_SHORT_NAME)
        rdm_addon_option.is_allowed = True
        rdm_addon_option.save()
        super(TestAuthViews, self).test_oauth_start()

    def test_oauth_finish(self):
        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        self.user.save()
        rdm_addon_option = get_rdm_addon_option(institution.id, self.ADDON_SHORT_NAME)
        rdm_addon_option.is_allowed = True
        rdm_addon_option.save()
        super(TestAuthViews, self).test_oauth_finish()

class TestConfigViews(GoogleDriveInstitutionsAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = {
        'path': 'Drive/Camera Uploads',
        'id': '1234567890'
    }
    Serializer = GoogleDriveInstitutionsSerializer
    client = GoogleDriveInstitutionsClient

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.mock_about = mock.patch.object(
            GoogleDriveInstitutionsClient,
            'rootFolderId'
        )
        self.mock_about.return_value = '24601'
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

    def test_import_auth(self):
        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        self.user.save()
        rdm_addon_option = get_rdm_addon_option(institution.id, self.ADDON_SHORT_NAME)
        rdm_addon_option.is_allowed = True
        rdm_addon_option.save()
        super(TestConfigViews, self).test_import_auth()

    @mock.patch.object(GoogleDriveInstitutionsClient, 'folders')
    def test_folder_list_not_root(self, mock_drive_client_folders):
        mock_drive_client_folders.return_value = sample_folder_data['files']
        folderId = '12345'
        self.node_settings.set_auth(external_account=self.external_account, user=self.user)
        self.node_settings.save()

        url = self.project.api_url_for('googledriveinstitutions_folder_list', folder_id=folderId)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), len(sample_folder_data['files']))

    @mock.patch.object(GoogleDriveInstitutionsClient, 'rootFolderId')
    def test_folder_list(self, mock_about):
        mock_about.return_value = '24601'
        super(TestConfigViews, self).test_folder_list()
