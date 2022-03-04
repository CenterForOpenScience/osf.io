import pytest
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

pytestmark = pytest.mark.django_db


class TestUpdateQuotaUserListByInstitutionStorageID(AdminTestCase):
    def setUp(self):
        super(TestUpdateQuotaUserListByInstitutionStorageID, self).setUp()
        self.user1 = AuthUserFactory(fullname='fullname1')
        self.institution = InstitutionFactory()
        self.user1.affiliated_institutions.add(self.institution)
        self.user1.save()

        self.view = views.UpdateQuotaUserListByInstitutionStorageID.as_view()

    def test_post_create_quota(self):
        max_quota = 50
        request = RequestFactory().post(
            reverse(
                'institutional_storage_quota_control'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1

        response = self.view(
            request,
            institution_id=self.institution.id
        )

        nt.assert_equal(response.status_code, 302)
        user_quota = UserQuota.objects.filter(
            user=self.user1, storage_type=UserQuota.CUSTOM_STORAGE
        ).first()
        nt.assert_is_not_none(user_quota)
        nt.assert_equal(user_quota.max_quota, max_quota)

    def test_post_update_quota(self):
        UserQuota.objects.create(user=self.user1, max_quota=100)
        max_quota = 150
        request = RequestFactory().post(
            reverse(
                'institutional_storage_quota_control:'
                'update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': max_quota})
        request.user = self.user1

        response = self.view(
            request,
            institution_id=self.institution.id
        )

        nt.assert_equal(response.status_code, 302)
        user_quota = UserQuota.objects.filter(
            user=self.user1, storage_type=UserQuota.CUSTOM_STORAGE
        ).first()
        nt.assert_is_not_none(user_quota)
        nt.assert_equal(user_quota.max_quota, max_quota)


class TestUserListByInstitutionStorageID(AdminTestCase):
    def setUp(self):
        super(TestUserListByInstitutionStorageID, self).setUp()
        self.user = AuthUserFactory(fullname='fullname')
        self.institution = InstitutionFactory()
        self.region = RegionFactory(_id=self.institution._id, name='Storage')
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.view = views.UserListByInstitutionStorageID()

    def test_get_user_list(self):
        request = RequestFactory().get(
            reverse(
                'institutional_storage_quota_control:institution_user_list',
                kwargs={'institution_id': self.institution.id}
            )
        )
        request.user = self.user

        view = setup_view(self.view, request,
                          institution_id=self.institution.id)
        user_list = view.get_userlist()

        nt.assert_equal(len(user_list), 1)
        nt.assert_equal(user_list[0]['fullname'], self.user.fullname)
        nt.assert_equal(user_list[0]['quota'], api_settings.DEFAULT_MAX_QUOTA)

    def test_get_institution(self):
        request = RequestFactory().get(
            reverse(
                'institutional_storage_quota_control:institution_user_list',
                kwargs={'institution_id': self.institution.id}
            )
        )
        request.user = self.user

        view = setup_view(self.view, request,
                          institution_id=self.institution.id)
        institution = view.get_institution()

        nt.assert_equal(institution.storage_name, self.region.name)

    def test_get_context_data_has_storage_name(self):
        request = RequestFactory().get(
            reverse(
                'institutional_storage_quota_control:institution_user_list',
                kwargs={'institution_id': self.institution.id}
            )
        )

        request.user = self.user

        view = setup_view(self.view, request,
                          institution_id=self.institution.id)
        view.object_list = view.get_queryset()
        res = view.get_context_data()

        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['institution_storage_name'], self.region.name)


class TestInstitutionStorageListByAdmin(AdminTestCase):
    def setUp(self):
        super(TestInstitutionStorageListByAdmin, self).setUp()
        self.user = AuthUserFactory(fullname='fullname')
        self.user.is_registered = True
        self.user.is_active = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.institution = InstitutionFactory()
        self.region = RegionFactory(_id=self.institution._id, name='Storage')
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.view = views.InstitutionStorageList.as_view()

    def test_get_redirect_to_user_list(self):
        request = RequestFactory().get(
            reverse(
                'institutional_storage_quota_control:list_institution_storage'
            )
        )
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

        request = RequestFactory().get(
            reverse(
                'institutional_storage_quota_control:list_institution_storage'
            )
        )
        request.user = self.user

        response = self.view(
            request,
        )

        nt.assert_equal(response.status_code, 200)
        nt.assert_is_not_none(Region.objects.filter(id=region1.id))
        nt.assert_is_not_none(Region.objects.filter(id=region2.id))
        nt.assert_is_instance(
            response.context_data['view'],
            views.InstitutionStorageList
        )

    def test_get_query_set(self):
        request = RequestFactory().get(
            reverse(
                'institutional_storage_quota_control:list_institution_storage'
            )
        )
        request.user = self.user
        view = views.InstitutionStorageList()
        view = setup_view(view, request)
        query_set = view.get_queryset()

        nt.assert_equal(query_set.exists(), True)
        nt.assert_equal(query_set.first().id, self.region.id)

    def test_get_context_data(self):
        request = RequestFactory().get(
            reverse(
                'institutional_storage_quota_control:list_institution_storage'
            )
        )
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
        self.user = AuthUserFactory(fullname='fullname')
        self.user.is_registered = True
        self.user.is_active = True
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.institution_1 = InstitutionFactory()
        self.region = RegionFactory(_id=self.institution._id, name='Storage')
        self.region_1 = RegionFactory(_id=self.institution_1._id,
                                      name='Storage_1')
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.view = views.InstitutionStorageList.as_view()

    def test_get_render_response(self):
        request = RequestFactory().get(
            reverse(
                'institutional_storage_quota_control:list_institution_storage'
            )
        )
        request.user = self.user

        response = self.view(
            request,
        )

        nt.assert_equal(response.status_code, 200)
        nt.assert_is_instance(
            response.context_data['view'],
            views.InstitutionStorageList
        )

    def test_get_query_set(self):
        request = RequestFactory().get(
            reverse(
                'institutional_storage_quota_control:list_institution_storage'
            )
        )
        request.user = self.user
        view = views.InstitutionStorageList()
        view = setup_view(view, request)
        query_set = view.get_queryset()

        nt.assert_equal(query_set.exists(), True)
        nt.assert_equal(len(query_set), 2)
