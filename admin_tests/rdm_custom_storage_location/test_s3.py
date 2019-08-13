from django.test import RequestFactory
import httplib
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
        self.mock_can_list = mock.patch('addons.s3.views.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()

        config = {
            'return_value.id': '12346789',
            'return_value.display_name': 's3.user',
            'return_value.Owner': 'Owner',
        }
        self.mock_uid = mock.patch('addons.s3.views.utils.get_user_info', **config)
        self.mock_uid.start()
        self.mock_exists = mock.patch('addons.s3.views.utils.bucket_exists')
        self.mock_exists.return_value = True
        self.mock_exists.start()

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
        return views.test_connection(request)

    def test_without_provider(self):
        params = {
            's3_access_key': '',
            's3_secret_key': ''
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Provider is missing.', request_post_response.content)

    def test_s3_settings_input_empty_keys(self):
        params = {
            's3_access_key': '',
            's3_secret_key': '',
            'provider_short_name': '',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Provider is missing.', request_post_response.content)

    def test_s3_settings_input_invalid_provider(self):
        params = {
            's3_access_key': '',
            's3_secret_key': '',
            'provider_short_name': 'invalidprovider',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Invalid provider.', request_post_response.content)

    def test_s3_settings_input_empty_keys_with_provider(self):
        params = {
            's3_access_key': '',
            's3_secret_key': '',
            'provider_short_name': 's3',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('All the fields above are required.', request_post_response.content)

    def test_s3_settings_input_empty_access_key(self):
        params = {
            's3_access_key': '',
            's3_secret_key': 'Non-empty-secret-key',
            'provider_short_name': 's3',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('All the fields above are required.', request_post_response.content)

    def test_s3_settings_input_empty_secret_key(self):
        params = {
            's3_access_key': 'Non-empty-secret-key',
            's3_secret_key': '',
            'provider_short_name': 's3',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('All the fields above are required.', request_post_response.content)

    @mock.patch('addons.s3.views.utils.can_list', return_value=False)
    def test_user_settings_cant_list(self, mock_can_list):
        params = {
            's3_access_key': 'Non-empty-secret-key',
            's3_secret_key': 'Non-empty-secret-key',
            'provider_short_name': 's3',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Unable to list buckets.', request_post_response.content)

    @mock.patch('addons.s3.views.utils.can_list', return_value=True)
    def test_user_settings_can_list(self, mock_can_list):
        params = {
            's3_access_key': 'Non-empty-secret-key',
            's3_secret_key': 'Non-empty-secret-key',
            'provider_short_name': 's3',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, httplib.OK)
        nt.assert_in('Credentials are valid', request_post_response.content)

    @mock.patch('addons.s3.views.utils.get_user_info', return_value=None)
    def test_user_settings_invalid_credentials(self, mock_uid):
        params = {
            's3_access_key': 'Non-empty-secret-key',
            's3_secret_key': 'Non-empty-secret-key',
            'provider_short_name': 's3',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Unable to access account.\\n'
                'Check to make sure that the above credentials are valid,'
                'and that they have permission to list buckets.', request_post_response.content)


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
        return views.save_credentials(request)

    def test_provider_missing(self):
        response = self.view_post({
            'storage_name': 'My storage',
            's3_access_key': 'Non-empty-access-key',
            's3_secret_key': 'Non-empty-secret-key',
            's3_bucket': 'Cute bucket',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content)

    def test_invalid_provider(self):
        response = self.view_post({
            'storage_name': 'My storage',
            's3_access_key': 'Non-empty-access-key',
            's3_secret_key': 'Non-empty-secret-key',
            's3_bucket': 'Cute bucket',
            'provider_short_name': 'invalidprovider',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Invalid provider.', response.content)

    @mock.patch('admin.rdm_custom_storage_location.utils.test_s3_connection')
    def test_success(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'Nice'}, httplib.OK
        response = self.view_post({
            'storage_name': 'My storage',
            's3_access_key': 'Non-empty-access-key',
            's3_secret_key': 'Non-empty-secret-key',
            's3_bucket': 'Cute bucket',
            'provider_short_name': 's3',
        })

        nt.assert_equals(response.status_code, httplib.OK)
        nt.assert_in('Saved credentials successfully!!', response.content)

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'My storage')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage']['access_key'], 'Non-empty-access-key')
        nt.assert_equals(wb_credentials['storage']['secret_key'], 'Non-empty-secret-key')

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 's3')
        nt.assert_equals(wb_settings['storage']['bucket'], 'Cute bucket')

    @mock.patch('admin.rdm_custom_storage_location.utils.test_s3_connection')
    def test_invalid_credentials(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'NG'}, httplib.BAD_REQUEST

        response = self.view_post({
            'storage_name': 'My storage',
            's3_access_key': 'Wrong-access-key',
            's3_secret_key': 'Wrong-secret-key',
            's3_bucket': 'Cute bucket',
            'provider_short_name': 's3',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('NG', response.content)
        nt.assert_false(Region.objects.filter(_id=self.institution._id).exists())
