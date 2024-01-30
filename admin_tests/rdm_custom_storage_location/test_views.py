import pytest
from django.test import RequestFactory
from django.http import Http404, HttpResponse
import json
from nose import tools as nt

from admin_tests.utilities import setup_user_view
from admin.rdm_custom_storage_location import views
from addons.osfstorage.models import Region
from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    RegionFactory,
    InstitutionFactory,
)
from django.core.exceptions import PermissionDenied


class TestInstitutionDefaultStorage(AdminTestCase):
    def setUp(self):
        super(TestInstitutionDefaultStorage, self).setUp()
        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user = AuthUserFactory()
        self.default_region = Region.objects.first()

        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution1)
        self.user.save()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionalStorageView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.addon_type_dict = [
            'BoxAddonAppConfig',
            'OSFStorageAddonAppConfig',
            'OwnCloudAddonAppConfig',
            'S3AddonAppConfig',
            'GoogleDriveAddonConfig',
            'SwiftAddonAppConfig',
            'S3CompatAddonAppConfig',
            'NextcloudAddonAppConfig',
            'DropboxBusinessAddonAppConfig',
            'NextcloudInstitutionsAddonAppConfig',
            'S3CompatInstitutionsAddonAppConfig',
            'OCIInstitutionsAddonAppConfig',
            'OneDriveBusinessAddonAppConfig',
        ]

    def test_admin_login(self):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_get(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_get_without_custom_storage(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        for addon in res.context_data['providers']:
            nt.assert_true(type(addon).__name__ in self.addon_type_dict)
        nt.assert_equal(res.context_data['region'], self.default_region)
        nt.assert_equal(res.context_data['selected_provider_short_name'], 'osfstorage')

    def test_get_custom_storage(self, *args, **kwargs):
        self.us = RegionFactory()
        self.us._id = self.institution1._id
        self.us.save()
        res = self.view.get(self.request, *args, **kwargs)
        for addon in res.context_data['providers']:
            nt.assert_true(type(addon).__name__ in self.addon_type_dict)
        nt.assert_equal(res.context_data['region'], self.us)
        nt.assert_equal(res.context_data['selected_provider_short_name'], res.context_data['region'].waterbutler_settings['storage']['provider'])


@pytest.mark.feature_202210
class TestIconView(AdminTestCase):
    def setUp(self):
        super(TestIconView, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view = views.IconView()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def tearDown(self):
        super(TestIconView, self).tearDown()
        self.user.delete()

    def test_login_user(self):
        nt.assert_true(self.view.test_func())

    def test_valid_get(self, *args, **kwargs):
        self.view.kwargs = {'addon_name': 's3'}
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_invalid_get(self, *args, **kwargs):
        self.view.kwargs = {'addon_name': 'invalidprovider'}
        with nt.assert_raises(Http404):
            self.view.get(self.request, *args, **self.view.kwargs)


@pytest.mark.feature_202210
class TestPermissionTestConnection(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory()

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.TestConnectionView.as_view()(request)

    def test_normal_user(self):
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_with_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        response = self.view_post({})
        nt.assert_is_instance(response, HttpResponse)

    def test_superuser(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "Provider is missing."}')

        response = self.view_post({'provider_short_name': 'test'})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "Invalid provider."}')


class TestPermissionSaveCredentials(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory()

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.SaveCredentialsView.as_view()(request)

    def test_normal_user(self):
        response = self.view_post({})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response._headers['location'][1], '/accounts/login/?next=/fake_path')

    def test_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response._headers['location'][1], '/accounts/login/?next=/fake_path')

    def test_staff_with_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        response = self.view_post({})
        nt.assert_is_instance(response, HttpResponse)

    def test_superuser(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response._headers['location'][1], '/accounts/login/?next=/fake_path')


class TestPermissionFetchTemporaryToken(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory()

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.FetchTemporaryTokenView.as_view()(request)

    def test_normal_user(self):
        response = self.view_post({})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response._headers['location'][1], '/accounts/login/?next=/fake_path')

    def test_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response._headers['location'][1], '/accounts/login/?next=/fake_path')

    def test_staff_with_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        response = self.view_post({})
        nt.assert_is_instance(response, HttpResponse)

    def test_superuser(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response._headers['location'][1], '/accounts/login/?next=/fake_path')
