from django.test import RequestFactory
from django.utils import timezone
import httplib
import json
from nose import tools as nt

from admin.rdm_custom_storage_location import views
from tests.base import AdminTestCase
from osf.models.external import ExternalAccountTemporary
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)


class TestSaveCredentials(AdminTestCase):
    def setUp(self):
        super(TestSaveCredentials, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()
        self.seed_data = {
            'provider_name': 'box',
            'oauth_key': 'pzN7NJr1EDzXDHsoZRqJT6jHVkt7ryhQbOzQjiduLmPw8CHs8lzrUBrBiztMQvxK5KLplhpKuGxeP91W',
            'oauth_secret': 'qgKnksgBkx76yCl9CqtTP4DOzPYiHLN9LSHFoVsgLgCc6ZqXngWMww5ydxrqY6OzyjUAcP5wL8c58D1Z',
            'expires_at': timezone.now(),
            'refresh_token': 'e97DkIMV6B0j6NjD1CYIiAm4',
            'date_last_refreshed': timezone.now(),
            'display_name': 'box display name is here',
            'profile_url': 'example.com',
            '_id': self.institution._id,
            'provider_id': '88080800880',
        }

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.fetch_temporary_token(request)

    def test_provider_missing(self):
        response = self.view_post({
            'no_pro': 'box',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content)

    def test_fail_Oauth_procedure_canceled(self):
        response = self.view_post({
            'provider_short_name': 'box',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Oauth permission procedure was canceled', response.content)

    def test_success(self):
        temp_account = ExternalAccountTemporary.objects.create(
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
            'provider_short_name': 'box',
        })
        nt.assert_equals(response.status_code, httplib.OK)
        data = json.loads(response.content)
        response_temp_account = data['response_data']
        nt.assert_equals(response_temp_account['display_name'], temp_account.display_name)
        nt.assert_equals(response_temp_account['oauth_key'], temp_account.oauth_key)
        nt.assert_equals(response_temp_account['provider'], temp_account.provider)
        nt.assert_equals(response_temp_account['provider_id'], temp_account.provider_id)
        nt.assert_equals(response_temp_account['provider_name'], temp_account.provider_name)
        nt.assert_equals(response_temp_account['fullname'], self.user.fullname)
