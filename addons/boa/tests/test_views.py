import mock
import pytest
from rest_framework import status as http_status

from addons.base.tests.views import OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
from addons.boa.tests.utils import BoaBasicAuthAddonTestCase
from osf_tests.factories import AuthUserFactory
from osf.utils import permissions
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db


class TestAuthViews(BoaBasicAuthAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    def test_oauth_start(self):
        """Not applicable to non-oauth add-ons."""
        pass

    def test_oauth_finish(self):
        """Not applicable to non-oauth add-ons."""
        pass


class TestConfigViews(BoaBasicAuthAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.mock_boa_client_login = mock.patch('boaapi.boa_client.BoaClient.login')
        self.mock_boa_client_close = mock.patch('boaapi.boa_client.BoaClient.close')
        self.mock_boa_client_login.start()
        self.mock_boa_client_close.start()

    def tearDown(self):
        self.mock_boa_client_close.stop()
        self.mock_boa_client_login.stop()
        super(TestConfigViews, self).tearDown()

    def test_folder_list(self):
        """Not applicable to remote computing add-ons."""
        pass

    def test_set_config(self):
        """Not applicable to remote computing add-ons."""
        pass

    def test_get_config(self):
        """Lacking coverage for remote computing add-ons and thus replaced by:
            * ``test_get_config_owner_with_external_account()``
            * ``test_get_config_owner_without_external_account()``
            * ``test_get_config_write_contrib_with_external_account()``
            * ``test_get_config_write_contrib_without_external_account()``
            * ``test_get_config_admin_contrib_with_external_account()``
            * ``test_get_config_admin_contrib_without_external_account()``
        """
        pass

    def test_get_config_unauthorized(self):
        """Lacking coverage for remote computing add-ons and thus replaced by:
            * ``test_get_config_read_contrib_with_valid_credentials()``
            * ``test_get_config_read_contrib_without_valid_credentials()``
        """
        pass

    def test_get_config_owner_with_external_account(self):

        self.node_settings.set_auth(self.external_account, self.user)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            self.user,
            self.client
        )
        assert self.node_settings.external_account is not None
        assert serialized['validCredentials'] is True

        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        assert serialized == res.json['result']

    def test_get_config_owner_without_external_account(self):

        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            self.user,
            self.client
        )
        assert self.node_settings.external_account is None
        assert serialized['validCredentials'] is False

        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        assert serialized == res.json['result']

    def test_get_config_write_contrib_with_external_account(self):

        user_write = AuthUserFactory()
        self.node_settings.set_auth(self.external_account, self.user)
        self.project.add_contributor(user_write, permissions=permissions.WRITE, auth=self.auth, save=True)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            user_write,
            self.client
        )
        assert self.node_settings.external_account is not None
        assert serialized['validCredentials'] is True

        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=user_write.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        assert serialized == res.json['result']

    def test_get_config_write_contrib_without_external_account(self):

        user_write = AuthUserFactory()
        self.project.add_contributor(user_write, permissions=permissions.WRITE, auth=self.auth, save=True)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            user_write,
            self.client
        )
        assert self.node_settings.external_account is None
        assert serialized['validCredentials'] is False

        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=user_write.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        assert serialized == res.json['result']

    def test_get_config_admin_contrib_with_external_account(self):

        user_admin = AuthUserFactory()
        self.node_settings.set_auth(self.external_account, self.user)
        self.project.add_contributor(user_admin, permissions=permissions.ADMIN, auth=self.auth, save=True)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            user_admin,
            self.client
        )
        assert self.node_settings.external_account is not None
        assert serialized['validCredentials'] is True

        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=user_admin.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        assert serialized == res.json['result']

    def test_get_config_admin_contrib_without_external_account(self):

        user_admin = AuthUserFactory()
        self.project.add_contributor(user_admin, permissions=permissions.ADMIN, auth=self.auth, save=True)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            user_admin,
            self.client
        )
        assert self.node_settings.external_account is None
        assert serialized['validCredentials'] is False

        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=user_admin.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        assert serialized == res.json['result']

    def test_get_config_read_contrib_with_valid_credentials(self):

        user_read_only = AuthUserFactory()
        self.project.add_contributor(user_read_only, permissions=permissions.READ, auth=self.auth, save=True)

        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        with mock.patch.object(type(self.Serializer()), 'credentials_are_valid', return_value=True):
            res = self.app.get(url, auth=user_read_only.auth, expect_errors=True)
            assert res.status_code == http_status.HTTP_403_FORBIDDEN

    def test_get_config_read_contrib_without_valid_credentials(self):

        user_read_only = AuthUserFactory()
        self.project.add_contributor(user_read_only, permissions=permissions.READ, auth=self.auth, save=True)

        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        with mock.patch.object(type(self.Serializer()), 'credentials_are_valid', return_value=False):
            res = self.app.get(url, auth=user_read_only.auth, expect_errors=True)
            assert res.status_code == http_status.HTTP_403_FORBIDDEN
