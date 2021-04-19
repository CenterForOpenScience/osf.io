# -*- coding: utf-8 -*-
from rest_framework import status as http_status

from boto.exception import S3ResponseError
import mock
from nose.tools import (assert_equal, assert_equals,
    assert_true, assert_in, assert_false)
import pytest

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory, AuthUserFactory, DraftRegistrationFactory, InstitutionFactory

from addons.base.tests.views import (
    OAuthAddonConfigViewsTestCaseMixin
)
from addons.onedrivebusiness.tests.utils import OneDriveBusinessAddonTestCase
import addons.onedrivebusiness.settings as onedrivebusiness_settings
from website.util import api_url_for
from admin.rdm_addons.utils import get_rdm_addon_option

pytestmark = pytest.mark.django_db

class TestOneDriveBusinessViews(OneDriveBusinessAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    def setUp(self):
        self.mock_get_region_external_account = mock.patch(
            'addons.onedrivebusiness.models.get_region_external_account'
        )
        self.mock_node_settings_oauth_provider_fetch_access_token = mock.patch(
            'addons.onedrivebusiness.models.NodeSettings.oauth_provider.fetch_access_token'
        )
        self.mock_node_settings_ensure_team_folder = mock.patch(
            'addons.onedrivebusiness.models.NodeSettings.ensure_team_folder'
        )
        external_account = mock.Mock()
        external_account.provider_id = 'user-11'
        external_account.oauth_key = 'key-11'
        external_account.oauth_secret = 'secret-15'
        mock_region_external_account = mock.Mock()
        mock_region_external_account.external_account = external_account
        self.mock_get_region_external_account.return_value = mock_region_external_account
        self.mock_node_settings_oauth_provider_fetch_access_token.return_value = 'mock-access-token-1234'

        self.mock_get_region_external_account.start()
        self.mock_node_settings_oauth_provider_fetch_access_token.start()
        self.mock_node_settings_ensure_team_folder.start()
        super(TestOneDriveBusinessViews, self).setUp()

    def tearDown(self):
        self.mock_node_settings_ensure_team_folder.stop()
        self.mock_node_settings_oauth_provider_fetch_access_token.stop()
        self.mock_get_region_external_account.stop()
        super(TestOneDriveBusinessViews, self).tearDown()

    def test_onedrivebusiness_get_node_settings_owner(self):
        self.node_settings.set_auth(self.external_account, self.user)
        self.node_settings.folder_id = 'bucket'
        self.node_settings.save()
        url = self.node_settings.owner.api_url_for('onedrivebusiness_get_config')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json['result']
        assert_equal(result['nodeHasAuth'], True)
        assert_equal(result['userIsOwner'], True)
        assert_equal(result['folder']['path'], self.node_settings.folder_id)

    def test_onedrivebusiness_get_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('onedrivebusiness_get_config')
        unauthorized = AuthUserFactory()
        ret = self.app.get(url, auth=unauthorized.auth, expect_errors=True)

        assert_equal(ret.status_code, 403)

    ## Overrides ##

    def test_folder_list(self):
        pass

    def test_set_config(self):
        pass

    def test_import_auth(self):
        pass

    def test_import_auth_cant_write_node(self):
        pass

    def test_import_auth_invalid_account(self):
        pass

    def test_deauthorize_node(self):
        pass
