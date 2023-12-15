import pytest
from django.test import RequestFactory
from nose import tools as nt

from addons.github.tests.factories import GitHubNodeSettingsFactory, GitHubAccountFactory
from addons.s3.tests.factories import (S3NodeSettingsFactory, S3AccountFactory, )
from admin.user_identification_information_admin import views
from admin_tests.utilities import setup_view, setup_log_view
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from tests.base import AdminTestCase
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser

pytestmark = pytest.mark.django_db


class TestUserIdentificationListView(AdminTestCase):

    def setUp(self):
        institution = InstitutionFactory()
        self.user = AuthUserFactory(fullname='Test User1')
        self.user.is_staff = False
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(institution)
        self.user.save()

        self.superuser = AuthUserFactory(fullname='Broken Matt Hardy')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.add_addon('github')
        self.superuser.add_addon('s3')
        self.superuser.save()

        self.admin_user = AuthUserFactory(fullname='Test User3')
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = False
        self.admin_user.affiliated_institutions.add(institution)
        self.admin_user.save()

        self.view_permission = views.UserIdentificationAdminListView
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.user_settings2 = self.superuser.get_addon('github')
        self.external_account2 = GitHubAccountFactory(provider_name='Github name')
        self.user_settings2.owner.external_accounts.add(self.external_account2)
        self.user_settings2.owner.save()
        self.GitHubNode_settings = GitHubNodeSettingsFactory(user_settings=self.user_settings2)

        self.user_settings2 = self.superuser.get_addon('s3')
        self.external_account2 = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings2.owner.external_accounts.add(self.external_account2)
        self.user_settings2.owner.save()
        self.S3Node_settings2 = S3NodeSettingsFactory(user_settings=self.user_settings2)

        self.anon = AnonymousUser()

    def test_get_userlist(self):
        list_name = []
        view = views.UserIdentificationAdminListView()
        view = setup_view(view, self.request)
        results = view.get_user_list()

        for i in range(len(results)):
            list_name.append(results[i]['fullname'])

        nt.assert_equal(len(results), 2)
        nt.assert_in(self.admin_user.fullname, list_name)
        nt.assert_in(self.user.fullname, list_name)

    def test_get_userlist_user_is_admin(self):
        self.request.user = self.admin_user
        view = views.UserIdentificationAdminListView()
        view = setup_view(view, self.request)
        results = view.get_user_list()

        nt.assert_is_instance(results, list)

    def test__permission_anonymous(self):
        self.request.user = self.anon
        with nt.assert_raises(PermissionDenied):
            views.UserIdentificationAdminListView.as_view()(self.request)

    def test__permission_normal_user(self):
        self.request.user = self.user
        with nt.assert_raises(PermissionDenied):
            views.UserIdentificationAdminListView.as_view()(self.request)

    def test__permission_superuser(self):
        self.request.user = self.superuser
        with nt.assert_raises(PermissionDenied):
            views.UserIdentificationAdminListView.as_view()(self.request)

    def test__permission_admin_with_institution(self):
        self.request.user = self.admin_user
        res = views.UserIdentificationAdminListView.as_view()(self.request)
        nt.assert_equal(res.status_code, 200)

    def test__permission_admin_without_institution(self):
        self.admin_user.affiliated_institutions = []
        self.request.user = self.admin_user
        with nt.assert_raises(PermissionDenied):
            views.UserIdentificationAdminListView.as_view()(self.request)

class TestUserIdentificationDetailView(AdminTestCase):

    def setUp(self):
        self.institution01 = InstitutionFactory()
        self.institution02 = InstitutionFactory()

        self.user = AuthUserFactory(fullname='Test User1')
        self.user.is_superuser = False
        self.user.is_staff = False
        self.user.affiliated_institutions.add(self.institution01)
        self.user.save()

        self.admin_user = AuthUserFactory(fullname='Broken Matt Hardy')
        self.admin_user.is_superuser = False
        self.admin_user.is_staff = True
        self.admin_user.affiliated_institutions.add(self.institution02)
        self.admin_user.save()

        self.superuser = AuthUserFactory(fullname='Test User3')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.view_permission = views.UserIdentificationDetailAdminView
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.admin_user

        self.admin_user.add_addon('s3')
        self.user_settings = self.admin_user.get_addon('s3')
        self.external_account = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.S3Node_settings = S3NodeSettingsFactory(user_settings=self.user_settings)
        self.S3Node_settings.save()

        self.anon = AnonymousUser()

    def test_get_object(self):
        view = views.UserIdentificationDetailAdminView()
        view = setup_log_view(view, self.request, guid=self.admin_user._id)
        results = view.get_object()
        nt.assert_is_instance(results, dict)

    def test__permission_anonymous(self):
        self.request.user = self.anon
        with nt.assert_raises(PermissionDenied):
            views.UserIdentificationDetailAdminView.as_view()(self.request, guid=self.user._id)

    def test__permission_normal_user(self):
        self.request.user = self.user
        with nt.assert_raises(PermissionDenied):
            views.UserIdentificationDetailAdminView.as_view()(self.request, guid=self.user._id)

    def test__permission_superuser(self):
        self.request.user = self.superuser
        with nt.assert_raises(PermissionDenied):
            views.UserIdentificationDetailAdminView.as_view()(self.request, guid=self.user._id)

    def test__permission_admin_with_institution(self):
        self.request.user = self.admin_user
        res = views.UserIdentificationDetailAdminView.as_view()(self.request, guid=self.admin_user._id)
        nt.assert_equal(res.status_code, 200)

    def test__permission_admin_with_guid_not_same_institution(self):
        self.request.user = self.admin_user
        with nt.assert_raises(PermissionDenied):
            views.UserIdentificationDetailAdminView.as_view()(self.request, guid=self.user._id)

    def test__permission_admin_without_institution(self):
        self.admin_user.affiliated_institutions = []
        self.request.user = self.admin_user
        with nt.assert_raises(PermissionDenied):
            views.UserIdentificationDetailAdminView.as_view()(self.request)

class TestExportFileCSVAdminView(AdminTestCase):

    def setUp(self):
        institution = InstitutionFactory()

        self.superuser = AuthUserFactory(fullname='Broken Matt Hardy')
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()

        self.admin_user = AuthUserFactory(fullname='Test User3')
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = False
        self.admin_user.affiliated_institutions.add(institution)
        self.admin_user.save()

        self.view_permission = views.ExportFileCSVAdminView
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.superuser

        self.superuser.add_addon('github')
        self.user_settings2 = self.superuser.get_addon('github')
        self.external_account2 = GitHubAccountFactory(provider_name='Github name')
        self.user_settings2.owner.external_accounts.add(self.external_account2)
        self.user_settings2.owner.save()
        self.GitHubNode_settings = GitHubNodeSettingsFactory(user_settings=self.user_settings2)

        self.superuser.add_addon('s3')
        self.user_settings2 = self.superuser.get_addon('s3')
        self.external_account2 = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings2.owner.external_accounts.add(self.external_account2)
        self.user_settings2.owner.save()
        self.S3Node_settings2 = S3NodeSettingsFactory(user_settings=self.user_settings2)

        self.anon = AnonymousUser()

        self.normal_user = AuthUserFactory(fullname='Broken Matt Hardy')
        self.normal_user.is_superuser = False
        self.normal_user.is_staff = False
        self.normal_user.save()

    def test__permission_anonymous(self):
        self.request.user = self.anon
        with nt.assert_raises(PermissionDenied):
            views.ExportFileCSVAdminView.as_view()(self.request)

    def test__permission_normal_user(self):
        self.request.user = self.normal_user
        with nt.assert_raises(PermissionDenied):
            views.ExportFileCSVAdminView.as_view()(self.request)

    def test__permission_superuser(self):
        self.request.user = self.superuser
        with nt.assert_raises(PermissionDenied):
            views.ExportFileCSVAdminView.as_view()(self.request)

    def test__permission_admin_with_institution(self):
        self.admin_user.affiliated_institutions.add(InstitutionFactory())
        self.request.user = self.admin_user
        res = views.ExportFileCSVAdminView.as_view()(self.request)
        nt.assert_equal(res.status_code, 200)

    def test__permission_admin_without_institution(self):
        self.admin_user.affiliated_institutions = []
        self.request.user = self.admin_user
        with nt.assert_raises(PermissionDenied):
            views.ExportFileCSVAdminView.as_view()(self.request)
