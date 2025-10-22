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
        return views.SaveCredentialsView.as_view()(request, institution_id=self.institution.id)

    def test_provider_missing(self):
        response = self.view_post({
            'no_pro': 'osfstorage',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        nt.assert_in('Provider is missing.', response.content.decode())

    def test_success(self):
        response = self.view_post({
            'provider_short_name': 'osfstorage',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('NII storage was set successfully', response.content.decode())

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
        nt.assert_in('NII storage was set successfully', response.content.decode())

        nt.assert_false(RegionExternalAccount.objects.filter(region=region).exists())
        nt.assert_false(ExternalAccount.objects.filter(id=external_account.id).exists())
        default_storage = Region.objects.first()
        #inst_storage = Region.objects.filter(id=region.id).first()
        inst_storage = Region.objects.get(id=region.id)
        nt.assert_equals(inst_storage.name, default_storage.name)
        nt.assert_equals(inst_storage.waterbutler_credentials,
                         default_storage.waterbutler_credentials)
        nt.assert_equals(inst_storage.waterbutler_settings,
                         default_storage.waterbutler_settings)
        nt.assert_equals(inst_storage.waterbutler_url,
                         default_storage.waterbutler_url)
        nt.assert_equals(inst_storage.mfr_url,
                         default_storage.mfr_url)

    def test_success_superuser(self):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        response = self.view_post({
            'provider_short_name': 'osfstorage',
        })

        nt.assert_equals(response.status_code, http_status.HTTP_200_OK)
        nt.assert_in('NII storage was set successfully', response.content.decode())
