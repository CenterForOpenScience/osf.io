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
            'nextcloud_host': 'drop database;',
            'nextcloud_username': 'invalid-user',
            'nextcloud_password': 'invalid-password',
            'nextcloud_folder': 'Hello World',
            'provider_short_name': 'nextcloud',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('NG', response.content.decode())
        nt.assert_false(Region.objects.filter(_id=self.institution._id).exists())

    @mock.patch('admin.rdm_custom_storage_location.utils.test_owncloud_connection')
    def test_success(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK

        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloud_host': 'valid.nextcloud.net',
            'nextcloud_username': 'admin',
            'nextcloud_password': '1234',
            'nextcloud_folder': 'reserved_for_osf',
            'provider_short_name': 'nextcloud',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Saved credentials successfully!!', response.content.decode())

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'My storage')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage']['host'], 'https://valid.nextcloud.net')
        nt.assert_equals(wb_credentials['storage']['username'], 'admin')
        nt.assert_equals(wb_credentials['storage']['password'], '1234')

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 'nextcloud')
        nt.assert_equals(wb_settings['storage']['folder'], '/reserved_for_osf/')

    @mock.patch('admin.rdm_custom_storage_location.utils.test_owncloud_connection')
    def test_success_superuser(self, mock_testconnection):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK

        response = self.view_post({
            'storage_name': 'My storage',
            'nextcloud_host': 'valid.nextcloud.net',
            'nextcloud_username': 'admin',
            'nextcloud_password': '1234',
            'nextcloud_folder': 'reserved_for_osf',
            'provider_short_name': 'nextcloud',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Saved credentials successfully!!', response.content.decode())

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'My storage')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage']['host'], 'https://valid.nextcloud.net')
        nt.assert_equals(wb_credentials['storage']['username'], 'admin')
        nt.assert_equals(wb_credentials['storage']['password'], '1234')

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 'nextcloud')
        nt.assert_equals(wb_settings['storage']['folder'], '/reserved_for_osf/')
