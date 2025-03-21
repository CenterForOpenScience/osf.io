import mock
import pytest
from nose import tools as nt

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location.utils import (
    get_providers, save_s3compatb3_credentials, wd_info_for_institutions, create_storage_info_template,
    get_osfstorage_info, get_institution_addon_info, get_s3_info, get_s3compat_info, get_s3compatinstitutions_info, get_ociinstitutions_info,
    get_nextcloudinstitutions_info, get_dropboxbusiness_info, get_institutional_storage_information
)
from osf_tests.factories import RegionFactory, InstitutionFactory
from tests.base import AdminTestCase
from rest_framework import status as http_status


@pytest.mark.feature_202210
class TestUtils:
    def test_get_providers(self):
        provider_list = get_providers()
        assert provider_list
        provider_list_short_name = [p.short_name for p in provider_list]
        nt.assert_in('s3', provider_list_short_name, 's3')
        nt.assert_in('dropboxbusiness', provider_list_short_name, 'dropboxbusiness')
        nt.assert_in('nextcloudinstitutions', provider_list_short_name, 'nextcloudinstitutions')
        nt.assert_in('osfstorage', provider_list_short_name, 'osfstorage')
        nt.assert_in('onedrivebusiness', provider_list_short_name, 'onedrivebusiness')
        nt.assert_in('swift', provider_list_short_name, 'swift')
        nt.assert_in('ociinstitutions', provider_list_short_name, 'ociinstitutions')
        nt.assert_in('s3compat', provider_list_short_name, 's3compat')
        nt.assert_in('s3compatinstitutions', provider_list_short_name, 's3compatinstitutions')

        provider_list = get_providers(available_list=[])
        nt.assert_equal(len(provider_list), 0)

        available_list = ['s3', 's3compat']
        provider_list = get_providers(available_list=available_list)
        provider_list_short_name = [p.short_name for p in provider_list]
        nt.assert_list_equal(provider_list_short_name, available_list)

    @mock.patch('osf.utils.external_util.remove_region_external_account')
    @mock.patch('admin.rdm_custom_storage_location.utils.update_storage')
    @mock.patch('admin.rdm_custom_storage_location.utils.test_s3compatb3_connection')
    def test_save_s3compatb3_credentials(self, mock_testconnection, mock_update_storage, mock_remove_region_external_account):
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK
        mock_update_storage.return_value = {}
        mock_remove_region_external_account.return_value = None
        response, status = save_s3compatb3_credentials('guid_test', 'My storage', 's3.compat.co.jp', 'Non-empty-access-key', 'Non-empty-secret-key', 'Cute bucket')
        nt.assert_equal(response, {'message': 'Saved credentials successfully!!'})
        nt.assert_equal(status, http_status.HTTP_200_OK)

    def test_wd_info_for_institutions(self):
        for_institution_providers = [
            's3compatinstitutions',
            'nextcloudinstitutions',
            'ociinstitutions',
            'dropboxbusiness',
            'onedrivebusiness',
        ]
        test_wd_credentials = {
            'storage': {
            },
        }
        for provider_name in for_institution_providers:
            wd_credentials, wd_settings = wd_info_for_institutions(provider_name)
            test_wb_settings = {
                'disabled': True,
                'storage': {
                    'provider': provider_name,
                    'type': Region.INSTITUTIONS,
                },
            }
            if provider_name == 's3compatinstitutions':
                test_wb_settings['encrypt_uploads'] = False
            nt.assert_equal(wd_credentials, test_wd_credentials)
            nt.assert_equal(wd_settings, test_wb_settings)


class TestStorageInformationUtils(AdminTestCase):
    def setUp(self):
        # Create mock objects
        self.mock_institution = mock.Mock()
        self.mock_institution.id = 'test_institution_id'

        self.mock_external_account = mock.Mock()
        self.mock_external_account.profile_url = 'https://test.com'
        self.mock_external_account.display_name = 'test_display_name'
        self.mock_external_account.oauth_key = 'test_oauth_key'

        self.mock_rdm_addon_option = mock.Mock()
        self.mock_rdm_addon_option.external_accounts.first.return_value = self.mock_external_account
        self.mock_rdm_addon_option.extended = {
            'base_folder': 'test_folder',
            'notification_secret': 'test_secret',
            'team_folder_id': 'test_team_folder'
        }

    def test_create_storage_info_template(self):
        """Test create_storage_info_template function"""
        result = create_storage_info_template('Test Title', 'Test Value')
        expected = {'field_name': 'Test Title', 'value': 'Test Value'}
        nt.assert_equal(result, expected)

    @mock.patch('admin.rdm_custom_storage_location.utils.get_rdm_addon_option')
    def test_get_institution_addon_info(self, mock_get_rdm_addon_option):
        """Test get_institution_addon_info function"""
        mock_get_rdm_addon_option.return_value = self.mock_rdm_addon_option

        rdm_addon_option, external_account = get_institution_addon_info(
            'test_institution_id', 'test_provider'
        )

        nt.assert_equal(external_account, self.mock_external_account)
        nt.assert_equal(rdm_addon_option, self.mock_rdm_addon_option)
        mock_get_rdm_addon_option.assert_called_once_with(
            'test_institution_id', 'test_provider', create=False
        )

    def test_get_osfstorage_info(self):
        """Test get_osfstorage_info function"""
        wb_settings = {'folder': 'test_folder'}
        result = get_osfstorage_info(wb_settings)

        expected = {
            'folder': {'field_name': 'Folder', 'value': 'test_folder'}
        }
        nt.assert_equal(result, expected)

    def test_get_s3_info(self):
        """Test get_s3_info function"""
        wb_credentials = {'access_key': 'test_key'}
        wb_settings = {
            'bucket': 'test_bucket',
            'encrypt_uploads': True
        }

        result = get_s3_info(wb_credentials, wb_settings)

        expected = {
            'access_key': {'field_name': 'Access Key', 'value': 'test_key'},
            'bucket': {'field_name': 'Bucket', 'value': 'test_bucket'},
            'encrypt_uploads': {'field_name': 'Enable Server Side Encryption', 'value': True}
        }
        nt.assert_equal(result, expected)

    def test_get_s3compat_info(self):
        """Test get_s3compat_info function"""
        wb_credentials = {
            'host': 'test_host',
            'access_key': 'test_key'
        }
        wb_settings = {
            'bucket': 'test_bucket',
            'encrypt_uploads': True
        }

        result = get_s3compat_info(wb_credentials, wb_settings)

        expected = {
            'host': {'field_name': 'Endpoint URL', 'value': 'test_host'},
            'access_key': {'field_name': 'Access Key', 'value': 'test_key'},
            'bucket': {'field_name': 'Bucket', 'value': 'test_bucket'},
            'encrypt_uploads': {'field_name': 'Enable Server Side Encryption', 'value': True}
        }
        nt.assert_equal(result, expected)

    @mock.patch('admin.rdm_custom_storage_location.utils.get_institution_addon_info')
    def test_get_s3compatinstitutions_info(self, mock_get_institution_addon_info):
        """Test get_s3compatinstitutions_info function"""
        mock_get_institution_addon_info.return_value = (self.mock_rdm_addon_option, self.mock_external_account)
        mock_region = mock.Mock()
        mock_region.waterbutler_settings = {'encrypt_uploads': True}

        result = get_s3compatinstitutions_info(
            self.mock_institution, 'test_provider', mock_region
        )

        expected = {
            'host': {'field_name': 'Endpoint URL', 'value': 'https://test.com'},
            'access_key': {'field_name': 'Access Key', 'value': 'test_display_name'},
            'bucket': {'field_name': 'Bucket', 'value': 'test_folder'},
            'encrypt_uploads': {'field_name': 'Enable Server Side Encryption', 'value': True}
        }
        nt.assert_equal(result, expected)

    @mock.patch('admin.rdm_custom_storage_location.utils.get_institution_addon_info')
    def test_get_ociinstitutions_info(self, mock_get_institution_addon_info):
        """Test get_ociinstitutions_info function"""
        mock_get_institution_addon_info.return_value = (self.mock_rdm_addon_option, self.mock_external_account)

        result = get_ociinstitutions_info(self.mock_institution, 'test_provider')

        expected = {
            'host': {'field_name': 'Endpoint URL', 'value': 'https://test.com'},
            'access_key': {'field_name': 'Access Key', 'value': 'test_display_name'},
            'bucket': {'field_name': 'Bucket', 'value': 'test_folder'}
        }
        nt.assert_equal(result, expected)

    @mock.patch('admin.rdm_custom_storage_location.utils.get_institution_addon_info')
    def test_get_nextcloudinstitutions_info(self, mock_get_institution_addon_info):
        """Test get_nextcloudinstitutions_info function"""
        mock_get_institution_addon_info.return_value = (self.mock_rdm_addon_option, self.mock_external_account)

        result = get_nextcloudinstitutions_info(self.mock_institution, 'test_provider')

        expected = {
            'host': {'field_name': 'Endpoint URL', 'value': 'https://test.com'},
            'username': {'field_name': 'Username', 'value': 'test_display_name'},
            'folder': {'field_name': 'Folder', 'value': 'test_folder'},
            'notification_secret': {
                'field_name': 'Connection common key from File Upload Notification App',
                'value': 'test_secret'
            }
        }
        nt.assert_equal(result, expected)

    @mock.patch('admin.rdm_custom_storage_location.utils.get_institution_addon_info')
    def test_get_dropboxbusiness_info(self, mock_get_institution_addon_info):
        """Test get_dropboxbusiness_info function"""
        mock_get_institution_addon_info.return_value = (self.mock_rdm_addon_option, self.mock_external_account)

        result = get_dropboxbusiness_info(self.mock_institution, 'test_provider')

        expected = {
            'authorized_by': {'field_name': 'authorized_by', 'value': 'test_display_name'},
        }
        nt.assert_equal(result, expected)

    def test_get_institutional_storage_information(self):
        """Test get_institutional_storage_information function"""
        region = RegionFactory()
        region.waterbutler_credentials = {
            'storage': {
                'access_key': 'test_key'
            }
        }
        region.waterbutler_settings = {
            'storage': {
                'bucket': 'test_bucket',
                'encrypt_uploads': True
            }
        }
        region.save()

        result = get_institutional_storage_information(
            's3', region, InstitutionFactory()
        )

        expected = {
            'access_key': {'field_name': 'Access Key', 'value': 'test_key'},
            'bucket': {'field_name': 'Bucket', 'value': 'test_bucket'},
            'encrypt_uploads': {'field_name': 'Enable Server Side Encryption', 'value': True}
        }
        nt.assert_equal(result, expected)

    def test_get_institutional_storage_information_unknown_provider(self):
        """Test get_institutional_storage_information function with unknown provider"""
        region = RegionFactory()
        region.waterbutler_credentials = {
            'storage': {
                'access_key': 'test_key'
            }
        }
        region.waterbutler_settings = {
            'storage': {
                'bucket': 'test_bucket',
                'encrypt_uploads': True
            }
        }
        region.save()

        result = get_institutional_storage_information(
            'unknown_provider', region, InstitutionFactory()
        )

        nt.assert_equal(result, {})
