from django.test import RequestFactory
from rest_framework import status as http_status
import json
import mock
from nose import tools as nt

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location import views
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from tests.base import AdminTestCase


class TestConnection(AdminTestCase):

    def setUp(self):
        super(TestConnection, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.TestConnectionView.as_view()(request)

    def test_empty_keys_with_provider(self):
        params = {
            's3compat_endpoint_url': '',
            's3compat_access_key': '',
            's3compat_secret_key': '',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3compat',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('All the fields above are required.', request_post_response.content.decode())

    def test_empty_access_key(self):
        params = {
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': '',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3compat',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('All the fields above are required.', request_post_response.content.decode())

    def test_empty_secret_key(self):
        params = {
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': '',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3compat',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('All the fields above are required.', request_post_response.content.decode())

    @mock.patch('addons.s3compat.views.utils.can_list', return_value=False)
    @mock.patch('addons.s3compat.views.utils.get_user_info', return_value=True)
    def test_user_settings_cant_list(self, mock_get_user_info, mock_can_list):
        params = {
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3compat',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Unable to list buckets.', request_post_response.content.decode())

    @mock.patch('addons.s3compat.views.utils.bucket_exists', return_value=False)
    @mock.patch('addons.s3compat.views.utils.can_list', return_value=True)
    @mock.patch('addons.s3compat.views.utils.get_user_info')
    def test_invalid_bucket(self, mock_get_user_info, mock_can_list, mock_bucket_exists):
        params = {
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3compat',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Invalid bucket.', request_post_response.content.decode())

    @mock.patch('addons.s3compat.views.utils.bucket_exists', return_value=True)
    @mock.patch('addons.s3compat.views.utils.can_list', return_value=True)
    @mock.patch('addons.s3compat.views.utils.get_user_info')
    def test_success(self, mock_get_user_info, mock_can_list, mock_bucket_exists):
        mock_get_user_info.return_value.id = '12346789'
        mock_get_user_info.return_value.display_name = 's3.user'

        params = {
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3compat',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Credentials are valid', request_post_response.content.decode())

    @mock.patch('addons.s3compat.views.utils.get_user_info', return_value=None)
    def test_invalid_credentials(self, mock_uid):
        params = {
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3compat',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Unable to access account.\\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list buckets.', request_post_response.content.decode())


class TestSaveCredentials(AdminTestCase):

    def setUp(self):
        super(TestSaveCredentials, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.SaveCredentialsView.as_view()(request)

    def test_provider_missing(self):
        response = self.view_post({
            'storage_name': 'My storage',
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-access-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Cute bucket',
            's3compat_server_side_encryption': 'False',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content.decode())

    def test_invalid_provider(self):
        response = self.view_post({
            'storage_name': 'My storage',
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-access-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Cute bucket',
            's3compat_server_side_encryption': 'False',
            'provider_short_name': 'invalidprovider',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Invalid provider.', response.content.decode())

    @mock.patch('admin.rdm_custom_storage_location.utils.test_s3compat_connection')
    def test_success(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK
        response = self.view_post({
            'storage_name': 'My storage',
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-access-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Cute bucket',
            's3compat_server_side_encryption': 'False',
            'provider_short_name': 's3compat',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Saved credentials successfully!!', response.content.decode())

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'My storage')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage']['access_key'], 'Non-empty-access-key')
        nt.assert_equals(wb_credentials['storage']['secret_key'], 'Non-empty-secret-key')

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 's3compat')
        nt.assert_equals(wb_settings['storage']['bucket'], 'Cute bucket')

    @mock.patch('admin.rdm_custom_storage_location.utils.test_s3compat_connection')
    def test_invalid_credentials(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'NG'}, http_status.HTTP_400_BAD_REQUEST

        response = self.view_post({
            'storage_name': 'My storage',
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Wrong-access-key',
            's3compat_secret_key': 'Wrong-secret-key',
            's3compat_bucket': 'Cute bucket',
            's3compat_server_side_encryption': 'False',
            'provider_short_name': 's3compat',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('NG', response.content.decode())
        nt.assert_false(Region.objects.filter(_id=self.institution._id).exists())
