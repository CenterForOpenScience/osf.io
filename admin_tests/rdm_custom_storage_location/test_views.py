from unittest import mock

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
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

    def test_unauthorized(self):
        self.request.user = AnonymousUser()
        nt.assert_false(self.view.test_func())

    def test_normal_user_login(self):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        nt.assert_false(self.view.test_func())

    def test_admin_login(self):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_admin_login_having_institution_id(self):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': 1}
        nt.assert_false(self.view.test_func())

    def test_super_login(self):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.affiliated_institutions.clear()
        self.view.kwargs = {'institution_id': 1}
        nt.assert_true(self.view.test_func())

    def test_super_login_missing_institution_id(self):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.affiliated_institutions.clear()
        nt.assert_false(self.view.test_func())

    def test_get(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_get_superuser(self, *args, **kwargs):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.affiliated_institutions.clear()
        kwargs = {**kwargs, 'institution_id': self.institution1.id}
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_get_institution_not_found(self, *args, **kwargs):
        self.request.user.affiliated_institutions.clear()
        with nt.assert_raises(Http404):
            self.view.get(self.request, *args, **kwargs)

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

    def test_get_storage_information(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.context_data['region'], self.default_region)
        nt.assert_equal(res.context_data['selected_provider_full_name'], 'NII Storage')
        nt.assert_equal(res.context_data['storage'], {
            'folder': {'field_name': 'Folder', 'value': self.default_region.waterbutler_settings.get('storage', {}).get('folder')}
        })
        nt.assert_true(res.context_data['disable_view_setting_info'])

    @mock.patch('admin.rdm_custom_storage_location.utils.get_institutional_storage_information')
    def test_get_storage_information_exception(self, mock_get_institutional_storage_information, *args, **kwargs):
        mock_get_institutional_storage_information.side_effect = Exception('test exception')
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.context_data['region'], self.default_region)
        nt.assert_equal(res.context_data['selected_provider_full_name'], 'NII Storage')
        nt.assert_equal(res.context_data['storage'], {})
        nt.assert_true(res.context_data['disable_view_setting_info'])


class TestInstitutionalStorageListView(AdminTestCase):
    def setUp(self):
        super(TestInstitutionalStorageListView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionalStorageListView()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def test_unauthorized(self):
        self.request.user = AnonymousUser()
        nt.assert_false(self.view.test_func())

    def test_admin_login(self):
        self.user.is_superuser = False
        self.user.is_staff = True
        nt.assert_false(self.view.test_func())

    def test_superuser_login(self):
        self.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_get_queryset(self):
        institution = InstitutionFactory()
        res = self.view.get_queryset()
        nt.assert_equal(len(res), 1)
        nt.assert_equal(res[0], institution)

    def test_get_context_data(self):
        self.view.object_list = self.view.get_queryset()
        res = self.view.get_context_data()
        nt.assert_is_not_none(res)


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
        self.institution = InstitutionFactory()
        self.institution_id = self.institution.id

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.TestConnectionView.as_view()(request, institution_id=self.institution_id)

    def test_unauthorized(self):
        self.user = AnonymousUser()
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_normal_user(self):
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_with_institution(self):
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        response = self.view_post({})
        nt.assert_is_instance(response, HttpResponse)

    def test_staff_with_other_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

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

    def test_superuser_institution_not_exist(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.institution_id = -1

        response = self.view_post({'provider_short_name': 'test'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.content, b'{"message": "Institution does not exist"}')


class TestPermissionSaveCredentials(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.institution_id = self.institution.id

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.SaveCredentialsView.as_view()(request, institution_id=self.institution_id)

    def test_unauthorized(self):
        self.user = AnonymousUser()
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_normal_user(self):
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_with_institution(self):
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        response = self.view_post({})
        nt.assert_is_instance(response, HttpResponse)

    def test_staff_with_other_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_superuser(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "Provider is missing."}')

        response = self.view_post({'provider_short_name': 'test'})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "Storage name is missing."}')

    def test_superuser_institution_not_exist(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.institution_id = -1

        response = self.view_post({'provider_short_name': 'test'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.content, b'{"message": "Institution does not exist"}')


class TestPermissionFetchCredentialsView(AdminTestCase):
    def setUp(self):
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.institution_id = self.institution.id

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.FetchCredentialsView.as_view()(request, institution_id=self.institution_id)

    def test_unauthorized(self):
        self.user = AnonymousUser()
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_normal_user(self):
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_with_institution(self):
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        response = self.view_post({})
        nt.assert_is_instance(response, HttpResponse)

        response = self.view_post({'provider_short_name': 'test'})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "unsupported"}')

    def test_staff_with_other_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_superuser(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "Provider is missing."}')

        response = self.view_post({'provider_short_name': 'test'})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "unsupported"}')

    def test_superuser_institution_not_exist(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.institution_id = -1

        response = self.view_post({'provider_short_name': 'test'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.content, b'{"message": "Institution does not exist"}')


class TestPermissionFetchTemporaryToken(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.institution_id = self.institution.id

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.FetchTemporaryTokenView.as_view()(request, institution_id=self.institution_id)

    def test_unauthorized(self):
        self.user = AnonymousUser()
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_normal_user(self):
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_with_institution(self):
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        response = self.view_post({})
        nt.assert_is_instance(response, HttpResponse)

    def test_staff_with_other_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_superuser(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "Provider is missing."}')

        response = self.view_post({'provider_short_name': 'test'})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "Oauth permission procedure was canceled"}')

    def test_superuser_institution_not_exist(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.institution_id = -1

        response = self.view_post({'provider_short_name': 'test'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.content, b'{"message": "Institution does not exist"}')


class TestPermissionRemoveTemporaryAuthData(AdminTestCase):
    def setUp(self):
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.institution_id = self.institution.id

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.is_ajax()
        request.user = self.user
        return views.RemoveTemporaryAuthData.as_view()(request, institution_id=self.institution_id)

    def test_unauthorized(self):
        self.user = AnonymousUser()
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_normal_user(self):
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_staff_with_institution(self):
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        response = self.view_post({})
        nt.assert_is_instance(response, HttpResponse)

    def test_staff_with_other_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_superuser(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 200)

    def test_superuser_institution_not_exist(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.institution_id = -1

        response = self.view_post({})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.content, b'{"message": "Institution does not exist"}')


class TestPermissionUserMapView(AdminTestCase):
    def setUp(self):
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.institution_id = self.institution.id
        self.test_binary_data = b''

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            data=params,
        )
        request.is_ajax()
        request.user = self.user
        request.FILES['usermap'] = self.test_binary_data
        return views.UserMapView.as_view()(request, institution_id=self.institution_id)

    def view_get(self, params):
        request = RequestFactory().get(
            'fake_path',
            data=params,
            content_type='application/json',
        )
        request.is_ajax()
        request.user = self.user
        return views.UserMapView.as_view()(request, institution_id=self.institution_id)

    # POST
    def test_post_unauthorized(self):
        self.user = AnonymousUser()
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_post_normal_user(self):
        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_post_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_post_staff_with_institution(self):
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        response = self.view_post({})
        nt.assert_is_instance(response, HttpResponse)

    def test_post_staff_with_other_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_post({})

    def test_post_superuser(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        response = self.view_post({})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "Provider is missing."}')

        response = self.view_post({'provider': 'test'})
        self.assertEquals(response.status_code, 200)

    def test_post_superuser_institution_not_exist(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.institution_id = -1

        response = self.view_post({'provider': 'test'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.content, b'{"message": "Institution does not exist"}')

    # GET
    def test_get_unauthorized(self):
        self.user = AnonymousUser()
        with nt.assert_raises(PermissionDenied):
            self.view_get({})

    def test_get_normal_user(self):
        with nt.assert_raises(PermissionDenied):
            self.view_get({})

    def test_get_staff_without_institution(self):
        self.user.is_staff = True
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_get({})

    def test_get_staff_with_institution(self):
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        response = self.view_get({})
        nt.assert_is_instance(response, HttpResponse)

    def test_get_staff_with_other_institution(self):
        institution = InstitutionFactory()

        self.user.is_staff = True
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        with nt.assert_raises(PermissionDenied):
            self.view_get({})

    def test_get_superuser(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        response = self.view_get({})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, b'{"message": "Provider is missing."}')

    def test_get_superuser_institution_not_exist(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.institution_id = -1

        response = self.view_get({'provider': 'test'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.content, b'{"message": "Institution does not exist"}')
