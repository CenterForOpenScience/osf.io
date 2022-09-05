import pytest
from django.http import Http404
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

pytestmark = pytest.mark.django_db


class TestUserIdentificationListView(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory(fullname='Test User1')
        self.user2 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user3 = AuthUserFactory(fullname='Test User3')
        self.user.is_superuser = False
        self.user2.is_superuser = True
        self.user3.is_staff = True
        self.user3.is_superuser = False

        self.view_permission = views.UserIdentificationAdminListView
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.user2.add_addon('github')
        self.user_settings2 = self.user2.get_addon('github')
        self.external_account2 = GitHubAccountFactory(provider_name='Github name')
        self.user_settings2.owner.external_accounts.add(self.external_account2)
        self.user_settings2.owner.save()
        self.GitHubNode_settings = GitHubNodeSettingsFactory(user_settings=self.user_settings2)

        self.user2.add_addon('s3')
        self.user_settings2 = self.user2.get_addon('s3')
        self.external_account2 = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings2.owner.external_accounts.add(self.external_account2)
        self.user_settings2.owner.save()
        self.S3Node_settings2 = S3NodeSettingsFactory(user_settings=self.user_settings2)

        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        self.user2.affiliated_institutions.add(institution)
        self.user.save()
        self.user2.save()
        self.user3.save()

    def test_get_userlist(self):
        list_name = []
        view = views.UserIdentificationAdminListView()
        view = setup_view(view, self.request)
        results = view.get_user_list()

        for i in range(len(results)):
            list_name.append(results[i]['fullname'])

        nt.assert_equal(len(results), 2)
        nt.assert_in(self.user2.fullname, list_name)
        nt.assert_in(self.user.fullname, list_name)

    def test_get_userlist_user_is_admin(self):
        self.request.user = self.user3
        view = views.UserIdentificationAdminListView()
        view = setup_view(view, self.request)
        results = view.get_user_list()

        nt.assert_is_instance(results, list)

    def test_get_userlist_permission_denied(self):
        self.request.user = self.user2
        view = views.UserIdentificationAdminListView()
        view = setup_view(view, self.request)

        with nt.assert_raises(Http404):
            view.get_user_list()


class TestUserIdentificationDetailView(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory(fullname='Test User1')
        self.user2 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user3 = AuthUserFactory(fullname='Test User3')

        self.user.is_superuser = False
        self.user2.is_superuser = False
        self.user3.is_superuser = True

        self.user.save()
        self.user2.save()
        self.user3.save()

        self.view_permission = views.UserIdentificationDetailAdminView
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user2

        self.user2.add_addon('s3')
        self.user_settings = self.user2.get_addon('s3')
        self.external_account = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.S3Node_settings = S3NodeSettingsFactory(user_settings=self.user_settings)
        self.S3Node_settings.save()

    def test_get_object_permission_denied(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user3
        view = views.UserIdentificationDetailAdminView()
        view = setup_log_view(view, request, guid=self.user3._id)
        with nt.assert_raises(Http404):
            view.get_object()

    def test_get_object(self):
        view = views.UserIdentificationDetailAdminView()
        view = setup_log_view(view, self.request, guid=self.user2._id)
        results = view.get_object()
        nt.assert_is_instance(results, dict)
