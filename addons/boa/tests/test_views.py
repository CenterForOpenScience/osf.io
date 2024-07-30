from unittest import mock
import pytest
from rest_framework import status as http_status

from addons.base.tests.views import OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
from addons.boa.tests.factories import BOA_HOST, BOA_PASSWORD
from addons.boa.tests.utils import BoaBasicAuthAddonTestCase
from addons.boa.boa_error_code import BoaErrorCode
from api.base.utils import waterbutler_api_url_for
from osf_tests.factories import AuthUserFactory
from osf.utils import permissions
from tests.base import OsfTestCase
from website import settings as osf_settings

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
        super().setUp()
        self.mock_boa_client_login = mock.patch('boaapi.boa_client.BoaClient.login')
        self.mock_boa_client_close = mock.patch('boaapi.boa_client.BoaClient.close')
        self.mock_boa_client_login.start()
        self.mock_boa_client_close.start()

    def tearDown(self):
        self.mock_boa_client_close.stop()
        self.mock_boa_client_login.stop()
        super().tearDown()

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

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
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

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
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

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
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

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
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

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
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

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
        res = self.app.get(url, auth=user_admin.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        assert serialized == res.json['result']

    def test_get_config_read_contrib_with_valid_credentials(self):

        user_read_only = AuthUserFactory()
        self.project.add_contributor(user_read_only, permissions=permissions.READ, auth=self.auth, save=True)

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
        with mock.patch.object(type(self.Serializer()), 'credentials_are_valid', return_value=True):
            res = self.app.get(url, auth=user_read_only.auth)
            assert res.status_code == http_status.HTTP_403_FORBIDDEN

    def test_get_config_read_contrib_without_valid_credentials(self):

        user_read_only = AuthUserFactory()
        self.project.add_contributor(user_read_only, permissions=permissions.READ, auth=self.auth, save=True)

        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
        with mock.patch.object(type(self.Serializer()), 'credentials_are_valid', return_value=False):
            res = self.app.get(url, auth=user_read_only.auth)
            assert res.status_code == http_status.HTTP_403_FORBIDDEN


class TestBoaSubmitViews(BoaBasicAuthAddonTestCase, OsfTestCase):

    def setUp(self):
        super().setUp()
        self.folder_name = 'fake_boa_folder'
        self.file_name = 'fake_boa_file.boa'
        self.file_size = 255
        self.dataset = 'fake_boa_dataset'
        self.download_url = f'{osf_settings.WATERBUTLER_URL}/v1/resources/{self.project._primary_key}/' \
                            f'providers/osfstorage/1a2b3c4d5e6f7g8'
        self.upload_url = f'{osf_settings.WATERBUTLER_URL}/v1/resources/{self.project._id}/' \
                          f'providers/osfstorage/8g7f6e5d4c3b2a1?kind=file'
        self.download_url_internal = f'{osf_settings.WATERBUTLER_INTERNAL_URL}/v1/resources/' \
                                     f'{self.project._primary_key}/providers/osfstorage/1a2b3c4d5e6f7g8'
        self.upload_url_internal = f'{osf_settings.WATERBUTLER_INTERNAL_URL}/v1/resources/' \
                                   f'{self.project._id}/providers/osfstorage/8g7f6e5d4c3b2a1?kind=file'
        self.payload_sub_folder = {
            'data': {
                'links': {'download': self.download_url, },
                'name': self.file_name,
                'materialized': f'/{self.folder_name}/{self.file_name}',
                'nodeId': self.project._id,
                'sizeInt': self.file_size,
            },
            'parent': {
                'links': {'upload': self.upload_url, },
            },
            'dataset': self.dataset,
        }
        self.payload_addon_root = {
            'data': {
                'links': {'download': self.download_url, },
                'name': self.file_name,
                'materialized': f'/{self.file_name}',
                'nodeId': self.project._id,
                'sizeInt': self.file_size,
            },
            'parent': {
                'isAddonRoot': True,
            },
            'dataset': self.dataset,
        }

    def tearDown(self):
        super().tearDown()

    def test_boa_submit_job_from_addon_root(self):
        with mock.patch('addons.boa.tasks.submit_to_boa.s', return_value=BoaErrorCode.NO_ERROR) as mock_submit_s:
            self.node_settings.set_auth(self.external_account, self.user)
            base_url = self.project.osfstorage_region.waterbutler_url
            addon_root_url = waterbutler_api_url_for(self.project._id, 'osfstorage', _internal=True, base_url=base_url)
            upload_url_root = f'{addon_root_url}?kind=file'
            url = self.project.api_url_for('boa_submit_job')
            res = self.app.post(url, json=self.payload_addon_root, auth=self.user.auth)
            assert res.status_code == http_status.HTTP_200_OK
            mock_submit_s.assert_called_with(
                BOA_HOST,
                mock.ANY,
                BOA_PASSWORD,
                self.user._id,
                self.project._id,
                self.dataset,
                self.file_name,
                self.file_size,
                f'/{self.file_name}',
                self.download_url_internal,
                upload_url_root,
            )

    def test_boa_submit_job_from_sub_folder(self):
        with mock.patch('addons.boa.tasks.submit_to_boa.s', return_value=BoaErrorCode.NO_ERROR) as mock_submit_s:
            self.node_settings.set_auth(self.external_account, self.user)
            url = self.project.api_url_for('boa_submit_job')
            res = self.app.post(url, json=self.payload_sub_folder, auth=self.user.auth)
            assert res.status_code == http_status.HTTP_200_OK
            mock_submit_s.assert_called_with(
                BOA_HOST,
                mock.ANY,
                BOA_PASSWORD,
                self.user._id,
                self.project._id,
                self.dataset,
                self.file_name,
                self.file_size,
                f'/{self.folder_name}/{self.file_name}',
                self.download_url_internal,
                self.upload_url_internal,
            )

    def test_boa_submit_job_admin_contrib(self):
        with mock.patch('addons.boa.tasks.submit_to_boa.s', return_value=BoaErrorCode.NO_ERROR) as mock_submit_s:
            self.node_settings.set_auth(self.external_account, self.user)
            user_admin = AuthUserFactory()
            self.project.add_contributor(user_admin, permissions=permissions.ADMIN, auth=self.auth, save=True)
            url = self.project.api_url_for('boa_submit_job')
            res = self.app.post(url, json=self.payload_sub_folder, auth=user_admin.auth)
            assert res.status_code == http_status.HTTP_200_OK
            mock_submit_s.assert_called_with(
                BOA_HOST,
                mock.ANY,
                BOA_PASSWORD,
                user_admin._id,
                self.project._id,
                self.dataset,
                self.file_name,
                self.file_size,
                f'/{self.folder_name}/{self.file_name}',
                self.download_url_internal,
                self.upload_url_internal,
            )

    def test_boa_submit_job_write_contrib(self):
        with mock.patch('addons.boa.tasks.submit_to_boa.s', return_value=BoaErrorCode.NO_ERROR) as mock_submit_s:
            self.node_settings.set_auth(self.external_account, self.user)
            user_write = AuthUserFactory()
            self.project.add_contributor(user_write, permissions=permissions.WRITE, auth=self.auth, save=True)
            url = self.project.api_url_for('boa_submit_job')
            res = self.app.post(url, json=self.payload_sub_folder, auth=user_write.auth)
            assert res.status_code == http_status.HTTP_200_OK
            mock_submit_s.assert_called_with(
                BOA_HOST,
                mock.ANY,
                BOA_PASSWORD,
                user_write._id,
                self.project._id,
                self.dataset,
                self.file_name,
                self.file_size,
                f'/{self.folder_name}/{self.file_name}',
                self.download_url_internal,
                self.upload_url_internal,
            )

    def test_boa_submit_job_read_contrib(self):
        with mock.patch('addons.boa.tasks.submit_to_boa.s', return_value=BoaErrorCode.NO_ERROR) as mock_submit_s:
            self.node_settings.set_auth(self.external_account, self.user)
            user_read_only = AuthUserFactory()
            self.project.add_contributor(user_read_only, permissions=permissions.READ, auth=self.auth, save=True)
            url = self.project.api_url_for('boa_submit_job')
            res = self.app.post(url, json=self.payload_sub_folder, auth=user_read_only.auth)
            assert res.status_code == http_status.HTTP_403_FORBIDDEN
            mock_submit_s.assert_not_called()
