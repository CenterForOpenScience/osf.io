import mock
import pytest
from admin.institutions import views
from django.test import RequestFactory
from django.urls import reverse
from nose import tools as nt
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory
)
from tests.base import AdminTestCase


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
