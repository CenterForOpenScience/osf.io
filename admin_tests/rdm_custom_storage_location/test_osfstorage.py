from django.test import RequestFactory
from rest_framework import status as http_status
import json
from nose import tools as nt

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location import views
from osf.models.region_external_account import RegionExternalAccount
from osf.models.external import ExternalAccount
from osf_tests.factories import (
    AuthUserFactory, InstitutionFactory, RegionFactory, ExternalAccountFactory
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
        return views.SaveCredentialsView.as_view()(request)

    def test_provider_missing(self):
        response = self.view_post({
            'no_pro': 'osfstorage',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content)

    def test_success(self):
        response = self.view_post({
            'provider_short_name': 'osfstorage',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('NII storage was set successfully', response.content)

    def test_success_cleanup_account(self):
        region = RegionFactory(_id=self.institution._id)
        external_account = ExternalAccountFactory(provider='box')
        RegionExternalAccount.objects.create(
            region=region,
            external_account=external_account
        )

        response = self.view_post({
            'provider_short_name': 'osfstorage',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('NII storage was set successfully', response.content)

        nt.assert_false(RegionExternalAccount.objects.filter(region=region).exists())
        nt.assert_false(ExternalAccount.objects.filter(id=external_account.id).exists())
        nt.assert_false(Region.objects.filter(id=region.id).exists())
