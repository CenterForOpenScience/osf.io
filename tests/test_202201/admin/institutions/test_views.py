import json
from operator import itemgetter
from nose import tools as nt
import mock
import pytest
from admin.institutions import views
from django.test import RequestFactory
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from api.base import settings as api_settings
from nose import tools as nt
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ProjectFactory,
    RegionFactory
)
from tests.base import AdminTestCase
from osf.models import Institution, Node, UserQuota
from admin_tests.utilities import setup_form_view, setup_user_view, setup_view
from admin.institutions import views
from admin.institutions.forms import InstitutionForm
from admin.base.forms import ImportFileForm


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
