from django.test import RequestFactory
import httplib
import json
from nose import tools as nt

from admin.rdm_custom_storage_location import views
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from tests.base import AdminTestCase


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
            'no_pro': 'osfstorage',
        })

        nt.assert_equals(response.status_code, httplib.BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content)

    def test_success(self):
        response = self.view_post({
            'provider_short_name': 'osfstorage',
        })

        nt.assert_equals(response.status_code, httplib.OK)
        nt.assert_in('NII storage was set successfully', response.content)
