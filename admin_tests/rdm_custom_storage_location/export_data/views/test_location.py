import json

import pytest
from django.test import RequestFactory
from nose import tools as nt
from rest_framework import status as http_status

from admin.rdm_custom_storage_location.export_data.views import location
from admin_tests.utilities import setup_view
from osf.models import ExportDataLocation
from osf_tests.factories import AuthUserFactory
from osf_tests.factories import (
    InstitutionFactory
)
from tests.base import AdminTestCase

pytestmark = pytest.mark.django_db


@pytest.mark.feature_202210
class TestExportStorageLocationViewBaseView(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.view_permission = location.ExportStorageLocationViewBaseView
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.user.save()
        self.view = location.ExportStorageLocationViewBaseView()
        self.institution = InstitutionFactory()

    def test_get_default_storage_location(self):
        view = setup_view(self.view, self.request)
        view.get_default_storage_location()

    def test_have_default_storage_location_id(self):
        view = setup_view(self.view, self.request)
        view.have_default_storage_location_id(1)

    def test_test_func(self):
        view = setup_view(self.view, self.request)
        view.test_func()

    def test_test_func_user_is_institutional_admin(self):
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution)

        view = setup_view(self.view, self.request)
        view.test_func()

    def test_is_affiliated_institution(self):
        institution_id = self.institution.id
        view = setup_view(self.view, self.request)
        view.is_affiliated_institution(institution_id)


@pytest.mark.feature_202210
class ExportStorageLocationView(AdminTestCase):
    def setUp(self):
        self.user = AuthUserFactory()
        self.view_permission = location.ExportStorageLocationView
        self.view = location.ExportStorageLocationView()
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.user.save()

    def test_get(self):
        view = setup_view(self.view, self.request)
        view.get(self.request)

    def test_get_queryset(self):
        view = setup_view(self.view, self.request)
        view.get_queryset()

    def test_get_context_data(self):
        view = setup_view(self.view, self.request)
        view.object_list = view.get_queryset()

        view.get_context_data()


@pytest.mark.feature_202210
class TestTestConnectionView(AdminTestCase):

    def setUp(self):
        super(TestTestConnectionView, self).setUp()
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
        return location.TestConnectionView.as_view()(request)

    def test_view_post_provider_short_name_empty(self):
        params = {
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': '',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_s3(self):
        params = {
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_s3compat(self):
        params = {
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3compat',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_nextcloudinstitutions(self):
        params = {
            'nextcloudinstitutions_host': 's3.compat.co.jp',
            'nextcloudinstitutions_username': 'Non-empty-secret-key',
            'nextcloudinstitutions_password': 'Non-empty-secret-key',
            'nextcloudinstitutions_folder': 'Water bucket',
            'provider_short_name': 'nextcloudinstitutions',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_dropboxbusiness(self):
        params = {
            'nextcloudinstitutions_host': 's3.compat.co.jp',
            'nextcloudinstitutions_username': 'Non-empty-secret-key',
            'nextcloudinstitutions_password': 'Non-empty-secret-key',
            'nextcloudinstitutions_folder': 'Water bucket',
            'provider_short_name': 'dropboxbusiness',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_provider_short_name_invalid(self):
        params = {
            'provider_short_name': 'invalidprovider',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)


@pytest.mark.feature_202210
class TestSaveCredentialsView(AdminTestCase):
    def setUp(self):
        super(TestSaveCredentialsView, self).setUp()
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
        return location.SaveCredentialsView.as_view()(request)

    def test_view_post_provider_short_name_empty(self):
        params = {
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': '',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_with_storage_name_empty(self):
        params = {
            'storage_name': '',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_s3_with_empty_storage_name(self):
        params = {
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3',
            'storage_name': '',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_s3(self):
        params = {
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3',
            'storage_name': 'test storage_name',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_s3compat(self):
        params = {
            's3compat_endpoint_url': 's3.compat.co.jp',
            's3compat_access_key': 'Non-empty-secret-key',
            's3compat_secret_key': 'Non-empty-secret-key',
            's3compat_bucket': 'Water bucket',
            'provider_short_name': 's3compat',
            'storage_name': 'test storage_name',

        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_nextcloudinstitutions(self):
        params = {
            'nextcloudinstitutions_host': 's3.compat.co.jp',
            'nextcloudinstitutions_username': 'Non-empty-secret-key',
            'nextcloudinstitutions_password': 'Non-empty-secret-key',
            'nextcloudinstitutions_folder': 'Water bucket',
            'nextcloudinstitutions_notification_secret': 'nextcloudinstitutions_notification_secret',
            'provider_short_name': 'nextcloudinstitutions',
            'storage_name': 'test storage_name',

        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_view_post_dropboxbusiness(self):
        params = {
            'provider_short_name': 'dropboxbusiness',
            'storage_name': 'test storage_name',
        }
        request_post_response = self.view_post(params)
        nt.assert_equals(request_post_response.status_code, http_status.HTTP_400_BAD_REQUEST)


@pytest.mark.feature_202210
class TestDeleteCredentialsView(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.user.save()
        self.institution = InstitutionFactory()
        self.view = location.DeleteCredentialsView()
        self.user.affiliated_institutions.add(self.institution)

    def test_delete_is_not_super_admin(self):
        user2 = AuthUserFactory()
        request = RequestFactory().get('/fake_path')
        user2.is_superuser = False
        user2.is_staff = True
        request.user = user2
        user2.affiliated_institutions.add(self.institution)
        user2.save()
        location.DeleteCredentialsView()

        export_location = ExportDataLocation.objects.create()

        view = setup_view(self.view, self.request, export_location.id)
        result = view.delete(self.request, export_location.id)

        nt.assert_equals(result.status_code, 403)

    def test_delete(self):
        export_location = ExportDataLocation.objects.create(institution_guid=self.institution.guid)

        view = setup_view(self.view, self.request, export_location.id)
        result = view.delete(self.request, export_location.id)

        nt.assert_equals(result.status_code, 200)

    def test_delete_exception(self):
        export_location = ExportDataLocation.objects.create()

        view = setup_view(self.view, self.request, export_location.id)
        result = view.delete(self.request, int(export_location.id) + 1)

        nt.assert_equals(result.status_code, 400)
