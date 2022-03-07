import pytest
from nose import tools as nt
from django.test import RequestFactory
from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    RegionFactory
)
from osf.models import Institution, UserQuota, OSFUser
from admin.institutions import views


@pytest.mark.skip('Clone test case from admin_tests/institutions/test_views.py for making coverage')
class TestQuotaUserList(AdminTestCase):
    def setUp(self):
        super(TestQuotaUserList, self).setUp()
        self.user = AuthUserFactory(fullname='fullname')
        self.institution = InstitutionFactory()
        self.region = RegionFactory(_id=self.institution._id, name='Storage')
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.view = views.QuotaUserList()
        self.view.get_userlist = self.get_userlist
        self.view.request = self.request
        self.view.paginate_by = 10
        self.view.kwargs = {}
        self.view.object_list = self.view.get_queryset()

    def get_institution(self):
        return self.institution

    def get_institution_has_storage_name(self):
        query = 'select name '\
                'from addons_osfstorage_region '\
                'where addons_osfstorage_region._id = osf_institution._id'
        institution = Institution.objects.filter(
            id=self.institution.id).extra(
            select={
                'storage_name': query,
            }
        )
        return institution.first()

    def get_userlist(self):
        user_list = []
        for user in OSFUser.objects.filter(
                affiliated_institutions=self.institution.id):
            user_list.append(self.view.get_user_quota_info(
                user, UserQuota.CUSTOM_STORAGE)
            )
        return user_list

    def test_get_user_quota_info_eppn_is_none(self):
        default_value_eppn = ''
        UserQuota.objects.create(user=self.user,
                                 storage_type=UserQuota.CUSTOM_STORAGE,
                                 max_quota=200)
        response = self.view.get_user_quota_info(
            self.user,
            storage_type=UserQuota.CUSTOM_STORAGE
        )

        nt.assert_is_not_none(response['eppn'])
        nt.assert_equal(response['eppn'], default_value_eppn)

    def test_get_context_data_has_not_storage_name(self):
        self.view.get_institution = self.get_institution
        UserQuota.objects.create(user=self.user,
                                 storage_type=UserQuota.CUSTOM_STORAGE,
                                 max_quota=200)

        response = self.view.get_context_data()

        nt.assert_is_instance(response, dict)
        nt.assert_false('institution_storage_name' in response)

    def test_get_context_data_has_storage_name(self):
        self.view.get_institution = self.get_institution_has_storage_name
        UserQuota.objects.create(user=self.user,
                                 storage_type=UserQuota.CUSTOM_STORAGE,
                                 max_quota=200)

        response = self.view.get_context_data()

        nt.assert_is_instance(response, dict)
        nt.assert_true('institution_storage_name' in response)
