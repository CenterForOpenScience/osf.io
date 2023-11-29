from io import BytesIO
from django.test import RequestFactory
from rest_framework import status as http_status
import json
import mock
from nose import tools as nt

from addons.osfstorage.models import Region
from addons.nextcloudinstitutions import settings
from admin.rdm_custom_storage_location import views
from osf.models import RdmAddonOption
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from tests.base import AdminTestCase


# TestConnection tests are on test_owncloud.py file.
# The reason it that they share the same implementation.

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
        return views.SaveCredentialsView.as_view()(request, institution_id=self.institution.id)

    @mock.patch('admin.rdm_custom_storage_location.utils.test_owncloud_connection')
    def test_connection_fail(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'NG'}, http_status.HTTP_400_BAD_REQUEST

        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloudinstitutions_host': 'drop database;',
            'nextcloudinstitutions_username': 'invalid-user',
            'nextcloudinstitutions_password': 'invalid-password',
            'nextcloudinstitutions_folder': 'Hello World',
            'provider_short_name': 'nextcloudinstitutions',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('NG', response.content.decode())
        nt.assert_false(Region.objects.filter(_id=self.institution._id).exists())

    @mock.patch('admin.rdm_custom_storage_location.utils.test_owncloud_connection')
    def test_success(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK

        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloudinstitutions_host': 'valid.nextcloud.net',
            'nextcloudinstitutions_username': 'admin',
            'nextcloudinstitutions_password': '1234',
            'nextcloudinstitutions_folder': 'reserved_for_osf',
            'provider_short_name': 'nextcloudinstitutions',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Saved credentials successfully!!', response.content.decode())

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'My storage')

        addonoption = RdmAddonOption.objects.filter(institution=self.institution).first()
        external_account = addonoption.external_accounts.first()
        nt.assert_is_not_none(external_account)
        nt.assert_equals(external_account.provider, 'nextcloudinstitutions')
        nt.assert_equals(external_account.provider_id, 'https://valid.nextcloud.net:admin')
        nt.assert_equals(external_account.oauth_secret, 'https://valid.nextcloud.net')
        nt.assert_equals(external_account.oauth_key, '1234')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage'], {})

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 'nextcloudinstitutions')
        nt.assert_equals(wb_settings['disabled'], True)

    @mock.patch('admin.rdm_custom_storage_location.utils.test_owncloud_connection')
    def test_success_superuser(self, mock_testconnection):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK

        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloudinstitutions_host': 'valid.nextcloud.net',
            'nextcloudinstitutions_username': 'admin',
            'nextcloudinstitutions_password': '1234',
            'nextcloudinstitutions_folder': 'reserved_for_osf',
            'provider_short_name': 'nextcloudinstitutions',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Saved credentials successfully!!', response.content.decode())

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'My storage')

        addonoption = RdmAddonOption.objects.filter(institution=self.institution).first()
        external_account = addonoption.external_accounts.first()
        nt.assert_is_not_none(external_account)
        nt.assert_equals(external_account.provider, 'nextcloudinstitutions')
        nt.assert_equals(external_account.provider_id, 'https://valid.nextcloud.net:admin')
        nt.assert_equals(external_account.oauth_secret, 'https://valid.nextcloud.net')
        nt.assert_equals(external_account.oauth_key, '1234')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage'], {})

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 'nextcloudinstitutions')
        nt.assert_equals(wb_settings['disabled'], True)


class TestFetchCredentialsView(AdminTestCase):
    def setUp(self):
        super(TestFetchCredentialsView, self).setUp()
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
        return views.FetchCredentialsView.as_view()(request, institution_id=self.institution.id)

    def view_get(self, url_params):
        request = RequestFactory().get('/fake_path?{}'.format(url_params))
        request.is_ajax()
        request.user = self.user
        return views.FetchCredentialsView.as_view()(request, institution_id=self.institution.id)

    def test_post_default(self):
        response = self.view_post({
            'provider_short_name': 'nextcloudinstitutions',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('nextcloudinstitutions_host'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_username'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_password'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_notification_secret'), None)
        nt.assert_equal(response_body.get('nextcloudinstitutions_folder'), settings.DEFAULT_BASE_FOLDER)

    def test_post(self):
        response = self.view_post({
            'provider_short_name': 'nextcloudinstitutions',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('nextcloudinstitutions_host'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_username'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_password'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_notification_secret'), None)
        nt.assert_equal(response_body.get('nextcloudinstitutions_folder'), settings.DEFAULT_BASE_FOLDER)

    def test_post_superuser(self):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        response = self.view_post({
            'provider_short_name': 'nextcloudinstitutions',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('nextcloudinstitutions_host'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_username'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_password'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_notification_secret'), None)
        nt.assert_equal(response_body.get('nextcloudinstitutions_folder'), settings.DEFAULT_BASE_FOLDER)

    def test_get_default(self):
        response = self.view_get('provider_short_name=nextcloudinstitutions')
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('nextcloudinstitutions_host'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_username'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_password'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_notification_secret'), None)
        nt.assert_equal(response_body.get('nextcloudinstitutions_folder'), settings.DEFAULT_BASE_FOLDER)

    def test_get_default_superuser(self):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        response = self.view_get('provider_short_name=nextcloudinstitutions')
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('nextcloudinstitutions_host'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_username'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_password'), '')
        nt.assert_equal(response_body.get('nextcloudinstitutions_notification_secret'), None)
        nt.assert_equal(response_body.get('nextcloudinstitutions_folder'), settings.DEFAULT_BASE_FOLDER)


class TestUserMapView(AdminTestCase):
    def setUp(self):
        super(TestUserMapView, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()
        string = f'#User_GUID(or ePPN),External_UserID,Fullname(ignored)\r\n' \
                 f'{self.user._id.upper()},test,{self.user.fullname.encode("utf-8")}'
        ng_string = '#User_GUID(or ePPN),External_UserID,Fullname(ignored)\r\n' \
                    '#Please input External users into the second column.\r\n' \
                    '\r\n' \
                    'EX5U2,,b"test1"\r\n' \
                    ',test2,b"test2"\r\n' \
                    'test@example.com,test3,'
        self.test_binary_data = BytesIO(string.encode('utf-8'))
        self.test_binary_data_ng = BytesIO(ng_string.encode('utf-8'))
        self.test_binary_data_invalid_format = BytesIO(b'test_invalid_format')

    def view_post(self, params, binary_data):
        request = RequestFactory().post(
            'fake_path',
            data=params,
        )
        request.is_ajax()
        request.user = self.user
        request.FILES['usermap'] = binary_data
        return views.UserMapView.as_view()(request, institution_id=self.institution.id)

    def view_get(self, params):
        request = RequestFactory().get(
            'fake_path',
            data=params,
        )
        request.is_ajax()
        request.user = self.user
        return views.UserMapView.as_view()(request, institution_id=self.institution.id)

    def test_post_ok(self):
        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloudinstitutions_host': 'valid.nextcloud.net',
            'nextcloudinstitutions_username': 'admin',
            'nextcloudinstitutions_password': '1234',
            'nextcloudinstitutions_folder': 'reserved_for_osf',
            'nextcloudinstitutions_notification_secret': '',
            'provider': 'nextcloudinstitutions',
        }, self.test_binary_data)
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('OK'), 1)
        nt.assert_equal(response_body.get('NG'), 0)
        nt.assert_equal(response_body.get('provider_name'), 'nextcloudinstitutions')
        nt.assert_equal(response_body.get('report'), [])
        nt.assert_equal(response_body.get('user_to_extuser'), {self.user._id: 'test'})

    def test_post_clear(self):
        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloudinstitutions_host': 'valid.nextcloud.net',
            'nextcloudinstitutions_username': 'admin',
            'nextcloudinstitutions_password': '1234',
            'nextcloudinstitutions_folder': 'reserved_for_osf',
            'nextcloudinstitutions_notification_secret': '',
            'provider': 'nextcloudinstitutions',
            'clear': True,
        }, self.test_binary_data)
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('OK'), 0)
        nt.assert_equal(response_body.get('NG'), 0)
        nt.assert_equal(response_body.get('provider_name'), 'nextcloudinstitutions')
        nt.assert_equal(response_body.get('report'), [])
        nt.assert_equal(response_body.get('user_to_extuser'), {})

    def test_post_ng_invalid_format(self):
        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloudinstitutions_host': 'valid.nextcloud.net',
            'nextcloudinstitutions_username': 'admin',
            'nextcloudinstitutions_password': '1234',
            'nextcloudinstitutions_folder': 'reserved_for_osf',
            'nextcloudinstitutions_notification_secret': '',
            'provider': 'nextcloudinstitutions',
        }, self.test_binary_data_invalid_format)
        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('OK'), 0)
        nt.assert_equal(response_body.get('NG'), 1)
        nt.assert_equal(response_body.get('provider_name'), 'nextcloudinstitutions')
        nt.assert_equal(response_body.get('report')[0], 'NG, INVALID_FORMAT: ')
        nt.assert_equal(response_body.get('user_to_extuser'), {})

    def test_post_ng(self):
        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloudinstitutions_host': 'valid.nextcloud.net',
            'nextcloudinstitutions_username': 'admin',
            'nextcloudinstitutions_password': '1234',
            'nextcloudinstitutions_folder': 'reserved_for_osf',
            'nextcloudinstitutions_notification_secret': '',
            'provider': 'nextcloudinstitutions',
            'check_extuser': True,
        }, self.test_binary_data_ng)
        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('OK'), 0)
        nt.assert_equal(response_body.get('NG'), 3)
        nt.assert_equal(response_body.get('provider_name'), 'nextcloudinstitutions')
        nt.assert_equal(response_body.get('report')[0], 'NG, EMPTY_EXTUSER: ')
        nt.assert_equal(response_body.get('report')[1], 'NG, EMPTY_USER: ')
        nt.assert_equal(response_body.get('report')[2], 'NG, UNKNOWN_USER: ')
        nt.assert_equal(response_body.get('user_to_extuser'), {})

    def test_post_ng_superuser(self):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloudinstitutions_host': 'valid.nextcloud.net',
            'nextcloudinstitutions_username': 'admin',
            'nextcloudinstitutions_password': '1234',
            'nextcloudinstitutions_folder': 'reserved_for_osf',
            'nextcloudinstitutions_notification_secret': '',
            'provider': 'nextcloudinstitutions',
        }, self.test_binary_data_ng)
        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        response_body = json.loads(response.content.decode())
        nt.assert_equal(response_body.get('OK'), 0)
        nt.assert_equal(response_body.get('NG'), 3)
        nt.assert_equal(response_body.get('provider_name'), 'nextcloudinstitutions')
        nt.assert_equal(response_body.get('report')[0], 'NG, EMPTY_EXTUSER: ')
        nt.assert_equal(response_body.get('report')[1], 'NG, EMPTY_USER: ')
        nt.assert_equal(response_body.get('report')[2], 'NG, UNKNOWN_USER: ')
        nt.assert_equal(response_body.get('user_to_extuser'), {})

    def test_get(self):
        response = self.view_get({
            'provider': 'nextcloudinstitutions',
        })
        test_content = f'#User_GUID(or ePPN),External_UserID,Fullname(ignored)\r\n' \
                       f'#Please input External users into the second column.\r\n' \
                       f'{self.user._id.upper()},,{self.user.fullname.encode("utf-8")}\r\n'
        binary_content = test_content.encode('utf-8')
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_equals(response.content, binary_content)

    def test_get_superuser(self):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        response = self.view_get({
            'provider': 'nextcloudinstitutions',
        })
        test_content = '#User_GUID(or ePPN),External_UserID,Fullname(ignored)\r\n'
        binary_content = test_content.encode('utf-8')
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_equals(response.content, binary_content)
