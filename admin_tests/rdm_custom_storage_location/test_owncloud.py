from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework import status as http_status
import json
import mock
import owncloud
import requests
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
        return views.TestConnectionView.as_view()(request, institution_id=self.institution.id)

    @mock.patch('owncloud.Client')
    def test_success_owncloud(self, mock_client):
        response = self.view_post({
            'owncloud_host': 'my-valid-host',
            'owncloud_username': 'my-valid-username',
            'owncloud_password': 'my-valid-password',
            'owncloud_folder': 'my-valid-folder',
            'provider_short_name': 'owncloud',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Credentials are valid', response.content.decode())

    @mock.patch('owncloud.Client')
    def test_success_nextcloud(self, mock_client):
        response = self.view_post({
            'nextcloud_host': 'my-valid-host',
            'nextcloud_username': 'my-valid-username',
            'nextcloud_password': 'my-valid-password',
            'nextcloud_folder': 'my-valid-folder',
            'provider_short_name': 'nextcloud',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Credentials are valid', response.content.decode())

    @mock.patch('owncloud.Client')
    def test_success_nextcloudinstitutions(self, mock_client):
        response = self.view_post({
            'nextcloudinstitutions_host': 'my-valid-host',
            'nextcloudinstitutions_username': 'my-valid-username',
            'nextcloudinstitutions_password': 'my-valid-password',
            'nextcloudinstitutions_folder': 'my-valid-folder',
            'provider_short_name': 'nextcloudinstitutions',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Credentials are valid', response.content.decode())

    @mock.patch('owncloud.Client')
    def test_connection_error(self, mock_client):
        mock_client.side_effect = requests.exceptions.ConnectionError()

        response = self.view_post({
            'owncloud_host': 'cuzidontcare',
            'owncloud_username': 'my-valid-username',
            'owncloud_password': 'my-valid-password',
            'owncloud_folder': 'my-valid-folder',
            'provider_short_name': 'owncloud',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Invalid ownCloud server.', response.content.decode())

    @mock.patch('owncloud.Client')
    def test_unauthorized(self, mock_client):
        res = HttpResponse(status=http_status.HTTP_401_UNAUTHORIZED)
        mock_client.side_effect = owncloud.owncloud.HTTPResponseError(res)

        response = self.view_post({
            'owncloud_host': 'my-valid-host',
            'owncloud_username': 'bad-username',
            'owncloud_password': 'bad-password',
            'owncloud_folder': 'my-valid-folder',
            'provider_short_name': 'owncloud',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_401_UNAUTHORIZED)
        nt.assert_in('ownCloud Login failed.', response.content.decode())

    @mock.patch('owncloud.Client')
    def test_invalid_folder_id(self, mock_client):
        res = HttpResponse(status=http_status.HTTP_400_BAD_REQUEST)
        mock_client.return_value.list.side_effect = owncloud.owncloud.HTTPResponseError(res)

        response = self.view_post({
            'owncloud_host': 'my-valid-host',
            'owncloud_username': 'my-valid-username',
            'owncloud_password': 'my-valid-password',
            'owncloud_folder': 'my-valid-folder',
            'provider_short_name': 'owncloud',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Invalid folder.', response.content.decode())


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
            'owncloud_host': 'drop database;',
            'owncloud_username': 'invalid-user',
            'owncloud_password': 'invalid-password',
            'owncloud_folder': 'Hello World',
            'provider_short_name': 'owncloud',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('NG', response.content.decode())
        nt.assert_false(Region.objects.filter(_id=self.institution._id).exists())

    @mock.patch('admin.rdm_custom_storage_location.utils.test_owncloud_connection')
    def test_success(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK

        response = self.view_post({
            'storage_name': 'My storage',
            'owncloud_host': 'valid.owncloud.net',
            'owncloud_username': 'admin',
            'owncloud_password': '1234',
            'owncloud_folder': 'reserved_for_osf',
            'provider_short_name': 'owncloud',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Saved credentials successfully!!', response.content.decode())

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'My storage')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage']['host'], 'https://valid.owncloud.net')
        nt.assert_equals(wb_credentials['storage']['username'], 'admin')
        nt.assert_equals(wb_credentials['storage']['password'], '1234')

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 'owncloud')
        nt.assert_equals(wb_settings['storage']['folder'], '/reserved_for_osf/')

    @mock.patch('admin.rdm_custom_storage_location.utils.test_owncloud_connection')
    def test_success_superuser(self, mock_testconnection):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK

        response = self.view_post({
            'storage_name': 'My storage',
            'owncloud_host': 'valid.owncloud.net',
            'owncloud_username': 'admin',
            'owncloud_password': '1234',
            'owncloud_folder': 'reserved_for_osf',
            'provider_short_name': 'owncloud',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Saved credentials successfully!!', response.content.decode())

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'My storage')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage']['host'], 'https://valid.owncloud.net')
        nt.assert_equals(wb_credentials['storage']['username'], 'admin')
        nt.assert_equals(wb_credentials['storage']['password'], '1234')

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 'owncloud')
        nt.assert_equals(wb_settings['storage']['folder'], '/reserved_for_osf/')
