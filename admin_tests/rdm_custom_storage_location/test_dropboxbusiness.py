import logging

from django.test import RequestFactory
from django.utils import timezone
from rest_framework import status as http_status
import json
import mock
from nose import tools as nt

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location import views
from admin_tests.rdm_addons.factories import RdmAddonOptionFactory
from osf.models.external import ExternalAccount
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from tests.base import AdminTestCase


class TestConnection(AdminTestCase):
    def setUp(self):
        super(TestConnection, self).setUp()
        self.institution = InstitutionFactory()
        self.institution_id = self.institution.id
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()
        self.f_option = RdmAddonOptionFactory(provider='dropboxbusiness', institution=self.institution)
        self.m_option = RdmAddonOptionFactory(provider='dropboxbusiness_manage', institution=self.institution)

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.TestConnectionView.as_view()(request, institution_id=self.institution_id)

    def test_provider_missing(self):
        response = self.view_post({
            'no_pro': 'dropboxbusiness',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content.decode())

    def test_no_token(self):
        response = self.view_post({
            'provider_short_name': 'dropboxbusiness',
            'storage_name': 'storage_name',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('No tokens.', response.content.decode())

    @mock.patch('addons.dropboxbusiness.utils.TeamInfo')
    @mock.patch('addons.dropboxbusiness.utils.addon_option_to_token')
    @mock.patch('addons.dropboxbusiness.utils.get_two_addon_options')
    def test_fail(self, mock_get_two_addon_options, mock_addon_option_to_token, mock_team_info):
        mock_get_two_addon_options.return_value = self.f_option, self.m_option
        mock_addon_option_to_token.return_value = 'Token'
        params = {
            'provider_short_name': 'dropboxbusiness',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Credentials are valid', request_post_response.content.decode())

    @mock.patch('addons.dropboxbusiness.utils.TeamInfo')
    @mock.patch('addons.dropboxbusiness.utils.addon_option_to_token')
    @mock.patch('addons.dropboxbusiness.utils.get_two_addon_options')
    def test_success(self, mock_get_two_addon_options, mock_addon_option_to_token, mock_team_info):
        mock_get_two_addon_options.return_value = self.f_option, self.m_option
        mock_addon_option_to_token.return_value = 'Token'
        params = {
            'provider_short_name': 'dropboxbusiness',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Credentials are valid', request_post_response.content.decode())

    @mock.patch('addons.dropboxbusiness.utils.TeamInfo')
    @mock.patch('addons.dropboxbusiness.utils.addon_option_to_token')
    @mock.patch('addons.dropboxbusiness.utils.get_two_addon_options')
    def test_success_superuser(self, mock_get_two_addon_options, mock_addon_option_to_token, mock_team_info):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        mock_get_two_addon_options.return_value = self.f_option, self.m_option
        mock_addon_option_to_token.return_value = 'Token'
        params = {
            'provider_short_name': 'dropboxbusiness',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Credentials are valid', request_post_response.content.decode())


class TestSaveCredentials(AdminTestCase):
    def setUp(self):
        super(TestSaveCredentials, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()
        self.seed_data = {
            'provider_name': 'dropboxbusiness',
            'oauth_key': 'pzN7NJr1EDzXDHsoZRqJT6jHVkt7ryhQbOzQjiduLmPw8CHs8lzrUBrBiztMQvxK5KLplhpKuGxeP91W',
            'oauth_secret': 'qgKnksgBkx76yCl9CqtTP4DOzPYiHLN9LSHFoVsgLgCc6ZqXngWMww5ydxrqY6OzyjUAcP5wL8c58D1Z',
            'expires_at': timezone.now(),
            'refresh_token': 'e97DkIMV6B0j6NjD1CYIiAm4',
            'date_last_refreshed': timezone.now(),
            'display_name': 'dropbox business display name is here',
            'profile_url': 'example.com',
            '_id': self.institution._id,
            'provider_id': '88080800880',
        }
        self.f_option = RdmAddonOptionFactory(provider='dropboxbusiness', institution=self.institution)
        self.m_option = RdmAddonOptionFactory(provider='dropboxbusiness_manage', institution=self.institution)

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.SaveCredentialsView.as_view()(request, institution_id=self.institution.id)

    def test_provider_missing(self):
        response = self.view_post({
            'no_pro': 'dropboxbusiness',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content.decode())

    def test_storage_name_missing(self):
        response = self.view_post({
            'provider_short_name': 'dropboxbusiness',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Storage name is missing.', response.content.decode())

    @mock.patch('addons.dropboxbusiness.utils.TeamInfo')
    @mock.patch('addons.dropboxbusiness.utils.addon_option_to_token')
    @mock.patch('addons.dropboxbusiness.utils.get_two_addon_options')
    def test_success(self, mock_get_two_addon_options, mock_addon_option_to_token, mock_team_info):
        mock_get_two_addon_options.return_value = self.f_option, self.m_option
        mock_addon_option_to_token.return_value = 'Token'

        ExternalAccount.objects.create(
            provider=self.seed_data['provider_name'],
            provider_name=self.seed_data['provider_name'],
            oauth_key=self.seed_data['oauth_key'],
            oauth_secret=self.seed_data['oauth_secret'],
            expires_at=self.seed_data['expires_at'],
            refresh_token=self.seed_data['refresh_token'],
            date_last_refreshed=self.seed_data['date_last_refreshed'],
            display_name=self.seed_data['display_name'],
            profile_url=self.seed_data['profile_url'],
            _id=self.seed_data['_id'],
            provider_id=self.seed_data['provider_id'],
        )
        response = self.view_post({
            'provider_short_name': 'dropboxbusiness',
            'storage_name': 'storage_name',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Dropbox Business was set successfully', response.content.decode())

        external_account = ExternalAccount.objects.get(
            provider=self.seed_data['provider_name'], provider_id=self.seed_data['provider_id'])
        nt.assert_equals(external_account.oauth_key, self.seed_data['oauth_key'])
        nt.assert_equals(external_account.oauth_secret, self.seed_data['oauth_secret'])

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'storage_name')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage'], {})

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 'dropboxbusiness')
        nt.assert_equals(wb_settings['disabled'], True)

    @mock.patch('addons.dropboxbusiness.utils.TeamInfo')
    @mock.patch('addons.dropboxbusiness.utils.addon_option_to_token')
    @mock.patch('addons.dropboxbusiness.utils.get_two_addon_options')
    def test_success_superuser(self, mock_get_two_addon_options, mock_addon_option_to_token, mock_team_info):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        mock_get_two_addon_options.return_value = self.f_option, self.m_option
        mock_addon_option_to_token.return_value = 'Token'

        ExternalAccount.objects.create(
            provider=self.seed_data['provider_name'],
            provider_name=self.seed_data['provider_name'],
            oauth_key=self.seed_data['oauth_key'],
            oauth_secret=self.seed_data['oauth_secret'],
            expires_at=self.seed_data['expires_at'],
            refresh_token=self.seed_data['refresh_token'],
            date_last_refreshed=self.seed_data['date_last_refreshed'],
            display_name=self.seed_data['display_name'],
            profile_url=self.seed_data['profile_url'],
            _id=self.seed_data['_id'],
            provider_id=self.seed_data['provider_id'],
        )
        response = self.view_post({
            'provider_short_name': 'dropboxbusiness',
            'storage_name': 'storage_name',
        })
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Dropbox Business was set successfully', response.content.decode())

        external_account = ExternalAccount.objects.get(
            provider=self.seed_data['provider_name'], provider_id=self.seed_data['provider_id'])
        nt.assert_equals(external_account.oauth_key, self.seed_data['oauth_key'])
        nt.assert_equals(external_account.oauth_secret, self.seed_data['oauth_secret'])

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        nt.assert_is_not_none(institution_storage)
        nt.assert_equals(institution_storage.name, 'storage_name')

        wb_credentials = institution_storage.waterbutler_credentials
        nt.assert_equals(wb_credentials['storage'], {})

        wb_settings = institution_storage.waterbutler_settings
        nt.assert_equals(wb_settings['storage']['provider'], 'dropboxbusiness')
        nt.assert_equals(wb_settings['disabled'], True)

    # Connection tests
    def test_no_token(self):
        response = self.view_post({
            'provider_short_name': 'dropboxbusiness',
            'storage_name': 'storage_name',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('No tokens.', response.content.decode())

    @mock.patch('addons.dropboxbusiness.utils.TeamInfo')
    @mock.patch('addons.dropboxbusiness.utils.addon_option_to_token')
    @mock.patch('addons.dropboxbusiness.utils.get_two_addon_options')
    def test_connection_success(self, mock_get_two_addon_options, mock_addon_option_to_token, mock_team_info):
        mock_get_two_addon_options.return_value = self.f_option, self.m_option
        mock_addon_option_to_token.return_value = 'Token'
        ExternalAccount.objects.create(
            provider=self.seed_data['provider_name'],
            provider_name=self.seed_data['provider_name'],
            oauth_key=self.seed_data['oauth_key'],
            oauth_secret=self.seed_data['oauth_secret'],
            expires_at=self.seed_data['expires_at'],
            refresh_token=self.seed_data['refresh_token'],
            date_last_refreshed=self.seed_data['date_last_refreshed'],
            display_name=self.seed_data['display_name'],
            profile_url=self.seed_data['profile_url'],
            _id=self.seed_data['_id'],
            provider_id=self.seed_data['provider_id'],
        )
        response = self.view_post({
            'provider_short_name': 'dropboxbusiness',
            'storage_name': 'storage_name',
        })

        logging.info(f'response: {response.content}')
        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Dropbox Business was set successfully', response.content.decode())

    def test_no_token_superuser(self):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        response = self.view_post({
            'provider_short_name': 'dropboxbusiness',
            'storage_name': 'storage_name',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('No tokens.', response.content.decode())

    @mock.patch('addons.dropboxbusiness.utils.TeamInfo')
    @mock.patch('addons.dropboxbusiness.utils.addon_option_to_token')
    @mock.patch('addons.dropboxbusiness.utils.get_two_addon_options')
    def test_connection_success_superuser(self, mock_get_two_addon_options, mock_addon_option_to_token, mock_team_info):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        mock_get_two_addon_options.return_value = self.f_option, self.m_option
        mock_addon_option_to_token.return_value = 'Token'
        ExternalAccount.objects.create(
            provider=self.seed_data['provider_name'],
            provider_name=self.seed_data['provider_name'],
            oauth_key=self.seed_data['oauth_key'],
            oauth_secret=self.seed_data['oauth_secret'],
            expires_at=self.seed_data['expires_at'],
            refresh_token=self.seed_data['refresh_token'],
            date_last_refreshed=self.seed_data['date_last_refreshed'],
            display_name=self.seed_data['display_name'],
            profile_url=self.seed_data['profile_url'],
            _id=self.seed_data['_id'],
            provider_id=self.seed_data['provider_id'],
        )
        response = self.view_post({
            'provider_short_name': 'dropboxbusiness',
            'storage_name': 'storage_name',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('Dropbox Business was set successfully', response.content.decode())
