import json
from operator import itemgetter
from django.urls import reverse
from nose import tools as nt
import mock
import pytest
from django.test import RequestFactory
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from api.base import settings as api_settings
from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ProjectFactory,
    RegionFactory
)
from osf.models import Institution, Node, UserQuota, OSFUser

from admin_tests.utilities import setup_form_view, setup_user_view, setup_view

from admin.institutions import views
from admin.institutions.forms import InstitutionForm
from admin.base.forms import ImportFileForm


@pytest.mark.skip('Clone test case from tests/test_quota.py for making coverage')
class TestUpdateQuotaUserListByInstitutionID(AdminTestCase):
    def setUp(self):
        super(TestUpdateQuotaUserListByInstitutionID, self).setUp()
        self.user1 = AuthUserFactory(fullname='fullname1')
        view_permission = Permission.objects.get(codename='change_osfuser')
        self.user1.user_permissions.add(view_permission)
        self.institution = InstitutionFactory()
        self.user1.affiliated_institutions.add(self.institution)
        self.user1.save()

        self.view = views.UpdateQuotaUserListByInstitutionID.as_view()

    def test_post_create_quota(self):
        max_quota = 50
        request = RequestFactory().post(
            reverse(
                'institutions'
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
            user=self.user1, storage_type=UserQuota.NII_STORAGE
        ).first()
        nt.assert_is_not_none(user_quota)
        nt.assert_equal(user_quota.max_quota, max_quota)

    def test_post_update_quota(self):
        UserQuota.objects.create(user=self.user1, max_quota=100)
        max_quota = 150
        request = RequestFactory().post(
            reverse(
                'institutions'
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
            user=self.user1, storage_type=UserQuota.NII_STORAGE
        ).first()
        nt.assert_is_not_none(user_quota)
        nt.assert_equal(user_quota.max_quota, max_quota)

    def test_UpdateQuotaUserListByInstitutionID_correct_view_permission(self):
        user = AuthUserFactory()

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': 20})

        request.user = user

        response = views.UpdateQuotaUserListByInstitutionID.as_view()(
            request, institution_id=self.institution.id
        )
        nt.assert_equal(response.status_code, 302)

    def test_UpdateQuotaUserListByInstitutionID_permission_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().post(
            reverse(
                'institutions'
                ':update_quota_institution_user_list',
                kwargs={'institution_id': self.institution.id}),
            {'maxQuota': 20})
        request.user = user

        with nt.assert_raises(PermissionDenied):
            views.UpdateQuotaUserListByInstitutionID.as_view()(
                request, institution_id=self.institution.id
            )


@pytest.mark.skip('Clone test case from admin_tests/institutions/test_views.py for making coverage')
class TestRecalculateQuota(AdminTestCase):
    def setUp(self):
        super(TestRecalculateQuota, self).setUp()

        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()

        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.user.affiliated_institutions.add(self.institution1)
        self.institution1.save()
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.url = reverse('institutions:institution_list')
        self.view = views.RecalculateQuota()
        self.view.request = self.request

    @mock.patch('website.util.quota.update_user_used_quota')
    @mock.patch('admin.institutions.views.OSFUser.objects')
    @mock.patch('admin.institutions.views.Institution.objects')
    def test_dispatch_method_with_user_is_superuser(self, mock_institution, mock_osfuser,
                                                    mock_update_user_used_quota_method):
        mock_institution.all.return_value = [self.institution1]
        mock_osfuser.filter.return_value = [self.user]

        response = self.view.dispatch(request=self.request)

        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, self.url)
        mock_institution.all.assert_called()
        mock_osfuser.filter.assert_called()
        mock_update_user_used_quota_method.assert_called()

    @mock.patch('website.util.quota.update_user_used_quota')
    @mock.patch('admin.institutions.views.OSFUser.objects')
    @mock.patch('admin.institutions.views.Institution.objects')
    def test_dispatch_method_with_user_is_not_superuser(self, mock_institution, mock_osfuser,
                                                        mock_update_user_used_quota_method):
        self.user.is_superuser = False
        self.user.save()

        mock_institution.all.return_value = [self.institution1]
        mock_osfuser.filter.return_value = [self.user]

        response = self.view.dispatch(request=self.request)

        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, self.url)
        mock_institution.all.assert_not_called()
        mock_osfuser.filter.assert_not_called()
        mock_update_user_used_quota_method.assert_not_called()


@pytest.mark.skip('Clone test case from admin_tests/institutions/test_views.py for making coverage')
class TestRecalculateQuotaOfUsersInInstitution(AdminTestCase):
    def setUp(self):
        super(TestRecalculateQuotaOfUsersInInstitution, self).setUp()

        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()

        self.user = AuthUserFactory()
        self.user.is_superuser = False
        self.user.is_staff = True
        self.user.affiliated_institutions.add(self.institution1)
        self.institution1.save()
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.url = reverse('institutions:statistical_status_default_storage')
        self.view = views.RecalculateQuotaOfUsersInInstitution()
        self.view.request = self.request

    @mock.patch('admin.institutions.views.Region.objects')
    @mock.patch('website.util.quota.update_user_used_quota')
    def test_dispatch_method_with_institution_exists_in_Region(self, mock_update_user_used_quota_method, mock_region):
        mock_region.filter.return_value.exists.return_value = True
        response = self.view.dispatch(request=self.request)

        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, self.url)
        mock_update_user_used_quota_method.assert_called()

    @mock.patch('admin.institutions.views.Region.objects')
    @mock.patch('website.util.quota.update_user_used_quota')
    def test_dispatch_method_with_institution_not_exists_in_Region(self, mock_update_user_used_quota_method,
                                                                   mock_region):
        mock_region.filter.return_value.exists.return_value = False
        response = self.view.dispatch(request=self.request)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, self.url)
        mock_update_user_used_quota_method.assert_not_called()

    @mock.patch('admin.institutions.views.Region.objects')
    @mock.patch('website.util.quota.update_user_used_quota')
    def test_dispatch_method_with_user_is_not_admin(self, mock_update_user_used_quota_method, mock_region):
        self.user.is_staff = False
        self.user.affiliated_institutions.remove(self.institution1)
        self.user.save()
        self.request.user = self.user
        mock_region.filter.return_value.exists.return_value = False
        response = self.view.dispatch(request=self.request)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, self.url)
        mock_update_user_used_quota_method.assert_not_called()


@pytest.mark.skip('Clone test case from tests/test_quota.py for making coverage')
class TestUserListByInstitutionID(AdminTestCase):

    def setUp(self):
        super(TestUserListByInstitutionID, self).setUp()
        self.user = AuthUserFactory(fullname='Alex fullname')
        self.user2 = AuthUserFactory(fullname='Kenny Dang')
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user2.affiliated_institutions.add(self.institution)
        self.user.save()
        self.user2.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = views.UserListByInstitutionID()
        self.view = setup_view(self.view,
                               self.request,
                               institution_id=self.institution.id)

    def test_default_user_list_by_institution_id(self, *args, **kwargs):

        res = self.view.get_userlist()
        nt.assert_is_instance(res, list)

    def test_search_email_by_institution_id(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'email': self.user2.username
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(res[0]['username'], self.user2.username)
        nt.assert_equal(len(res), 1)

    def test_search_guid_by_institution_id(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'guid': self.user2._id
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(res[0]['id'], self.user2._id)
        nt.assert_equal(len(res), 1)

    def test_search_name_by_institution_id(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'info': 'kenny'
            }
        )
        request.user = self.user

        view = views.UserListByInstitutionID()
        view = setup_view(view, request, institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(len(res), 1)
        nt.assert_in(res[0]['fullname'], self.user2.fullname)

    def test_search_name_guid_email_inputted(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'email': 'test@gmail.com',
                'guid': self.user._id,
                'info': 'kenny'
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(res[0]['id'], self.user._id)
        nt.assert_in(res[0]['fullname'], self.user.fullname)
        nt.assert_equal(len(res), 1)

    def test_search_not_found(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'email': 'sstest@gmail.com',
                'guid': 'guid2',
                'info': 'guid2'
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(len(res), 0)

@pytest.mark.skip('Clone test case from tests/test_quota.py for making coverage')
class TestExportFileTSV(AdminTestCase):
    def setUp(self):
        super(TestExportFileTSV, self).setUp()
        self.user = AuthUserFactory(fullname='Kenny Michel',
                                    username='Kenny@gmail.com')
        self.user2 = AuthUserFactory(fullname='alex queen')
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user2.affiliated_institutions.add(self.institution)
        self.user.save()
        self.user2.save()
        self.view = views.ExportFileTSV()

    def test_get(self):
        request = RequestFactory().get(
            'institutions:tsvexport',
            kwargs={'institution_id': self.institution.id})
        request.user = self.user
        view = setup_view(self.view, request,
                          institution_id=self.institution.id)
        res = view.get(request)

        result = res.content.decode('utf-8')

        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res['content-type'], 'text/tsv')
        nt.assert_in('kenny', result)
        nt.assert_in('alex queen', result)
        nt.assert_in('kenny@gmail.com', result)


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
