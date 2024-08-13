from unittest import mock
import pytest
from rest_framework import status as http_status

from addons.base.tests.views import OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
from addons.owncloud.tests.utils import OwnCloudBasicAuthAddonTestCase
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db


class TestAuthViews(OwnCloudBasicAuthAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    def test_oauth_start(self):
        pass

    def test_oauth_finish(self):
        pass


class TestConfigViews(OwnCloudBasicAuthAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):

    def setUp(self):
        super().setUp()
        self.mock_owncloud_login = mock.patch('owncloud.Client.login')
        self.mock_owncloud_logout = mock.patch('owncloud.Client.logout')
        self.mock_owncloud_login.start()
        self.mock_owncloud_logout.start()

    def tearDown(self):
        self.mock_owncloud_logout.stop()
        self.mock_owncloud_login.stop()
        super().tearDown()

    @mock.patch('addons.owncloud.models.NodeSettings.get_folders')
    def test_folder_list(self, mock_get_folders):
        mock_get_folders.return_value = ['/Documents/', '/Pictures/', '/Videos/']
        super().test_folder_list()

    def test_get_config(self):
        """Lacking coverage for non-oauth add-ons and thus replaced by:
            * ``test_get_config_with_external_account()``
            * ``test_get_config_without_external_account()``
        """
        pass

    def test_get_config_with_external_account(self):

        self.node_settings.set_auth(self.external_account, self.user)
        serialized = self.Serializer().serialize_settings(self.node_settings, self.user)
        assert self.node_settings.external_account is not None
        assert serialized['validCredentials'] is True

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        assert serialized == res.json['result']

    def test_get_config_without_external_account(self):

        serialized = self.Serializer().serialize_settings(self.node_settings, self.user)
        assert self.node_settings.external_account is None
        assert serialized['validCredentials'] is False

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        assert serialized == res.json['result']
