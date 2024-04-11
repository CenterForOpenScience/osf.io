import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied

from addons.osfstorage.models import Region
from admin.institutional_storage_quota_control import views
from django.test import RequestFactory
from django.urls import reverse
from nose import tools as nt
from osf.models import UserQuota
from admin_tests.utilities import setup_view
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    RegionFactory
)
from tests.base import AdminTestCase
from api.base import settings as api_settings
from django.http import Http404
from django.urls.exceptions import NoReverseMatch

pytestmark = pytest.mark.django_db


class TestUpdateQuotaUserListByInstitutionStorageID(AdminTestCase):
    def setUp(self):
        super(TestUpdateQuotaUserListByInstitutionStorageID, self).setUp()
        self.institution01 = InstitutionFactory(name='inst01')
        self.institution02 = InstitutionFactory(name='inst02')

        self.anon = AnonymousUser()

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

        self.view_name = 'institutional_storage_quota_control:update_quota_institution_user_list'
        self.view = views.UpdateQuotaUserListByInstitutionStorageID.as_view()

    def test__anonymous(self):
        max_quota = 50
        request = RequestFactory().post(
            reverse(self.view_name,
                    kwargs={'institution_id': self.institution01.id}),
            {'maxQuota': max_quota})
        request.user = self.anon
        with self.assertRaises(PermissionDenied):
            self.view(request, institution_id=self.institution01.id)

    def test__superuser(self):
        new_max_quota = 50
        upd_max_quota = 150

        # create user quota of inst01
        request = RequestFactory().post(
            reverse(self.view_name,
                    kwargs={'institution_id': self.institution01.id}),
            {'maxQuota': new_max_quota})
        request.user = self.superuser
        response = self.view(request, institution_id=self.institution01.id)

        nt.assert_equal(response.status_code, 302)
        new_user_quota_1 = UserQuota.objects.filter(
            user=self.institution01_admin, storage_type=UserQuota.CUSTOM_STORAGE
        ).first()
        nt.assert_is_not_none(new_user_quota_1)
        nt.assert_equal(new_user_quota_1.max_quota, new_max_quota)

        # update user quota of inst01
        request = RequestFactory().post(
            reverse(self.view_name,
                    kwargs={'institution_id': self.institution01.id}),
            {'maxQuota': upd_max_quota})
        request.user = self.superuser
        response = self.view(request, institution_id=self.institution01.id)

        nt.assert_equal(response.status_code, 302)
        upd_user_quota_1 = UserQuota.objects.filter(
            user=self.institution01_admin, storage_type=UserQuota.CUSTOM_STORAGE
        ).first()
        nt.assert_equal(upd_user_quota_1.max_quota, upd_max_quota)
        nt.assert_equal(upd_user_quota_1.id, new_user_quota_1.id)

        # create user quota of inst02
        request = RequestFactory().post(
            reverse(self.view_name,
                    kwargs={'institution_id': self.institution02.id}),
            {'maxQuota': new_max_quota})
        request.user = self.superuser
        response = self.view(request, institution_id=self.institution02.id)

        nt.assert_equal(response.status_code, 302)
        new_user_quota_2 = UserQuota.objects.filter(
            user=self.institution02_admin, storage_type=UserQuota.CUSTOM_STORAGE
        ).first()
        nt.assert_is_not_none(new_user_quota_2)
        nt.assert_equal(new_user_quota_2.max_quota, new_max_quota)

    def test__institutional_admin(self):
        new_max_quota = 100

        # create user quota of inst01
        request = RequestFactory().post(
            reverse(self.view_name,
                    kwargs={'institution_id': self.institution01.id}),
            {'maxQuota': new_max_quota})
        request.user = self.institution01_admin
        response = self.view(request, institution_id=self.institution01.id)

        nt.assert_equal(response.status_code, 302)
        new_user_quota_1 = UserQuota.objects.filter(
            user=self.institution01_admin, storage_type=UserQuota.CUSTOM_STORAGE
        ).first()
        nt.assert_is_not_none(new_user_quota_1)
        nt.assert_equal(new_user_quota_1.max_quota, new_max_quota)

        # create user quota of inst02
        request = RequestFactory().post(
            reverse(self.view_name,
                    kwargs={'institution_id': self.institution02.id}),
            {'maxQuota': new_max_quota})
        request.user = self.institution01_admin
        with self.assertRaises(PermissionDenied):
            self.view(request, institution_id=self.institution02.id)


class TestUserListByInstitutionStorageID(AdminTestCase):
    def setUp(self):
        super(TestUserListByInstitutionStorageID, self).setUp()
        self.institution01 = InstitutionFactory(name='inst01')
        self.institution02 = InstitutionFactory(name='inst02')

        self.region01 = RegionFactory(_id=self.institution01._id, name='Storage 01')
        self.region02 = RegionFactory(_id=self.institution02._id, name='Storage 02')

        self.anon = AnonymousUser()

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

        self.view_name = 'institutional_storage_quota_control:institution_user_list'
        self.view = views.UserListByInstitutionStorageID.as_view()
        self.view_instance = views.UserListByInstitutionStorageID()

    def test__anonymous(self):
        request = RequestFactory().get(
            reverse(
                self.view_name,
                kwargs={'institution_id': self.institution01.id}
            )
        )
        request.user = self.anon
        with self.assertRaises(PermissionDenied):
            self.view(request, institution_id=self.institution01.id)

    def test__superuser(self):
        # access inst01
        request = RequestFactory().get(
            reverse(
                self.view_name,
                kwargs={'institution_id': self.institution01.id}
            )
        )
        request.user = self.superuser
        response = self.view(request, institution_id=self.institution01.id)
        nt.assert_equal(response.status_code, 200)

        # access inst02
        request = RequestFactory().get(
            reverse(
                self.view_name,
                kwargs={'institution_id': self.institution02.id}
            )
        )
        request.user = self.superuser
        response = self.view(request, institution_id=self.institution02.id)
        nt.assert_equal(response.status_code, 200)

    def test__institutional_admin(self):
        # access inst01
        request = RequestFactory().get(
            reverse(
                self.view_name,
                kwargs={'institution_id': self.institution01.id}
            )
        )
        request.user = self.institution01_admin
        response = self.view(request, institution_id=self.institution01.id)
        nt.assert_equal(response.status_code, 200)

        # access inst02
        request = RequestFactory().get(
            reverse(
                self.view_name,
                kwargs={'institution_id': self.institution02.id}
            )
        )
        request.user = self.institution01_admin
        with self.assertRaises(PermissionDenied):
            self.view(request, institution_id=self.institution02.id)

    def test_get_userlist(self):
        request = RequestFactory().get(
            reverse(
                self.view_name,
                kwargs={'institution_id': self.institution01.id}
            )
        )
        request.user = self.institution01_admin

        view = setup_view(self.view_instance, request,
                          institution_id=self.institution01.id)
        view.institution_id = self.institution01.id
        user_list = view.get_userlist()

        nt.assert_equal(len(user_list), 1)
        nt.assert_equal(user_list[0]['fullname'], self.institution01_admin.fullname)
        nt.assert_equal(user_list[0]['quota'], api_settings.DEFAULT_MAX_QUOTA)

    def test_get_institution(self):
        request = RequestFactory().get(
            reverse(
                self.view_name,
                kwargs={'institution_id': self.institution01.id}
            )
        )
        request.user = self.institution01_admin

        view = setup_view(self.view_instance, request,
                          institution_id=self.institution01.id)
        institution = view.get_institution()

        nt.assert_equal(institution.storage_name, self.region01.name)

    def test_get_context_data_has_storage_name(self):
        request = RequestFactory().get(
            reverse(
                self.view_name,
                kwargs={'institution_id': self.institution01.id}
            )
        )

        request.user = self.institution01_admin

        view = setup_view(self.view_instance, request,
                          institution_id=self.institution01.id)
        view.institution_id = self.institution01.id
        view.object_list = view.get_queryset()
        res = view.get_context_data()

        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['institution_storage_name'], self.region01.name)

    def test__institution_id_not_exist(self):
        request = RequestFactory().get(
            reverse(
                self.view_name,
                kwargs={'institution_id': 0}
            )
        )
        request.user = self.superuser
        with self.assertRaises(Http404):
            self.view(request, institution_id=0)

    def test__institution_id_not_valid(self):
        with self.assertRaises(NoReverseMatch):
            RequestFactory().get(
                reverse(
                    self.view_name,
                    kwargs={'institution_id': 'fake_id'}
                )
            )

class TestAccessInstitutionStorageList(AdminTestCase):
    def setUp(self):
        super(TestAccessInstitutionStorageList, self).setUp()
        self.institution01 = InstitutionFactory(name='inst01')
        self.institution02 = InstitutionFactory(name='inst02')

        self.region01 = RegionFactory(_id=self.institution01._id, name='Storage 01')
        self.region02 = RegionFactory(_id=self.institution02._id, name='Storage 02')

        self.anon = AnonymousUser()

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

        self.view_name = 'institutional_storage_quota_control:list_institution_storage'
        self.view = views.InstitutionStorageList.as_view()
        self.view_instance = views.InstitutionStorageList()

    def test__anonymous(self):
        request = RequestFactory().get(reverse(self.view_name))
        request.user = self.anon
        with self.assertRaises(PermissionDenied):
            self.view(request)

    def test__superuser(self):
        # access inst01
        request = RequestFactory().get(reverse(self.view_name))
        request.user = self.superuser
        response = self.view(request)
        nt.assert_equal(response.status_code, 200)

    def test__institutional_admin(self):
        request = RequestFactory().get(reverse(self.view_name))
        request.user = self.institution01_admin
        response = self.view(request, institution_id=self.institution01.id)
        nt.assert_equal(response.status_code, 302)


class TestInstitutionStorageListByAdmin(AdminTestCase):
    def setUp(self):
        super(TestInstitutionStorageListByAdmin, self).setUp()
        self.institution = InstitutionFactory()
        self.region = RegionFactory(_id=self.institution._id, name='Storage')

        self.user = AuthUserFactory(fullname='fullname')
        self.user.is_registered = True
        self.user.is_active = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.view_name = 'institutional_storage_quota_control:list_institution_storage'
        self.view = views.InstitutionStorageList.as_view()

    def test_get_redirect_to_user_list(self):
        request = RequestFactory().get(reverse(self.view_name))
        request.user = self.user

        response = self.view(
            request,
            institution_id=self.institution.id
        )

        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url,
                        '/institutional_storage_quota_control'
                        '/user_list_by_institution_id/{}/'.format(
                            self.institution.id
                        ))

    def test_get_render_response(self):
        inst1 = InstitutionFactory()
        inst2 = InstitutionFactory()
        region1 = RegionFactory(_id=inst1._id, name='Storage1')
        region2 = RegionFactory(_id=inst2._id, name='Storage2')
        self.user.affiliated_institutions.add(inst1)
        self.user.save()

        request = RequestFactory().get(reverse(self.view_name))
        request.user = self.user

        response = self.view(request)

        nt.assert_equal(response.status_code, 200)
        nt.assert_is_not_none(Region.objects.filter(id=region1.id))
        nt.assert_is_not_none(Region.objects.filter(id=region2.id))
        nt.assert_is_instance(
            response.context_data['view'],
            views.InstitutionStorageList
        )

    def test_get_query_set(self):
        request = RequestFactory().get(reverse(self.view_name))
        request.user = self.user
        view = views.InstitutionStorageList()
        view = setup_view(view, request)
        query_set = view.get_queryset()

        nt.assert_equal(query_set.exists(), True)
        nt.assert_equal(query_set.first().id, self.region.id)

    def test_get_context_data(self):
        request = RequestFactory().get(reverse(self.view_name))
        request.user = self.user
        view = views.InstitutionStorageList()
        view = setup_view(view, request)
        view.object_list = view.get_queryset()

        res = view.get_context_data()

        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['view'], views.InstitutionStorageList)


class TestInstitutionStorageListBySuperUser(AdminTestCase):
    def setUp(self):
        super(TestInstitutionStorageListBySuperUser, self).setUp()
        self.institution = InstitutionFactory()
        self.institution_1 = InstitutionFactory()

        self.region = RegionFactory(_id=self.institution._id, name='Storage')
        self.region_1 = RegionFactory(_id=self.institution_1._id, name='Storage_1')

        self.user = AuthUserFactory(fullname='fullname')
        self.user.is_registered = True
        self.user.is_active = True
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.view_name = 'institutional_storage_quota_control:list_institution_storage'
        self.view = views.InstitutionStorageList.as_view()

    def test_get_render_response(self):
        request = RequestFactory().get(reverse(self.view_name))
        request.user = self.user

        response = self.view(request)

        nt.assert_equal(response.status_code, 200)
        nt.assert_is_instance(
            response.context_data['view'],
            views.InstitutionStorageList
        )

    def test_get_query_set(self):
        request = RequestFactory().get(reverse(self.view_name))
        request.user = self.user
        view = views.InstitutionStorageList()
        view = setup_view(view, request)
        query_set = view.get_queryset()

        nt.assert_equal(query_set.exists(), True)
        nt.assert_equal(len(query_set), 2)
