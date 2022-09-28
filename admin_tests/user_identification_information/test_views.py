from operator import itemgetter

import mock
import pytest
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse
from nose import tools as nt

from addons.github.tests.factories import GitHubNodeSettingsFactory, GitHubAccountFactory
from addons.s3.tests.factories import (S3UserSettingsFactory, S3NodeSettingsFactory, S3AccountFactory, )
from admin.user_identification_information import views
from admin_tests.utilities import setup_view, setup_log_view, setup_user_view
from osf.models import UserQuota
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ExternalAccountFactory,
)
from tests.base import AdminTestCase

pytestmark = pytest.mark.django_db


class TestUserIdentificationInformationListView(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory(fullname='Test User1')
        self.user2 = AuthUserFactory(fullname='Test User2')
        self.user3 = AuthUserFactory(fullname='Test User3')
        self.user.is_superuser = True
        self.view_permission = views.UserIdentificationInformationListView
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        external_account = ExternalAccountFactory()
        external_account.provider = 's3'
        external_account.provider_name = 'Amazon S3'
        external_account.save()

        NodeSettingsFactory = S3NodeSettingsFactory()
        NodeSettingsFactory.save()

        UserSettingsFactory = S3UserSettingsFactory()
        UserSettingsFactory.save()

        institution = InstitutionFactory()
        institution.name = 'test institution'
        self.user.affiliated_institutions.add(institution)

        self.user.save()
        self.user2.save()
        self.user3.save()

    def test_get_user_quota_info(self):
        self.user.eppn = 'freddiemercury+10866790@cos.io'
        self.email = 'testaddemail@gmail.com'
        self.user.emails.create(address=self.email)
        self.user.save()

        UserQuota.objects.create(user=self.user, storage_type=UserQuota.NII_STORAGE, max_quota=200, used=1000)

        view = views.UserIdentificationInformationListView()
        view.kwargs = {'guid': self.user._id}
        result = view.get_user_quota_info(self.user, UserQuota.NII_STORAGE)

        nt.assert_equal(self.user.fullname, result['fullname'])
        nt.assert_equal(self.user.eppn, result['eppn'])

    def test_get_queryset(self):
        view = views.UserIdentificationListView()
        view = setup_view(view, self.request)
        results = view.get_user_list()
        nt.assert_is_instance(results, list)

    @mock.patch('admin.user_identification_information.views.UserIdentificationInformationListView.get_queryset')
    def test_get_queryset_mock_get_queryset(self, mock_method):
        mock_method.self.get_queryset.return_value = [
            {'id': 'z298m', 'fullname': 'Test User1', 'eppn': '', 'affiliation': '', 'email': 'freddiemercury+12331754@cos.io',
             'last_login': '', 'usage': 0, 'usage_value': 0.0, 'usage_abbr': 'KB', 'extended_storage': ''},
            {'id': 'n2dch', 'fullname': 'Broken Matt Hardy', 'eppn': '', 'affiliation': '',
             'email': 'freddiemercury+12422709@cos.io', 'last_login': '', 'usage': 0, 'usage_value': 0.0, 'usage_abbr': 'KB',
             'extended_storage': '/Github name\n/Amazon S3'}]
        view = views.UserIdentificationInformationListView()
        view = setup_view(view, self.request)
        view.get_queryset()
        assert mock_method.called

    @mock.patch('admin.user_identification_information.views.UserIdentificationInformationListView.get_context_data')
    def test_get_context_data(self, mock_method):
        mock_method.self.get_queryset.return_value = [
            {'id': 'dsyem', 'fullname': 'superuser01', 'eppn': '', 'email': 'superuser01@example.com.vn', 'usage': 1352,
             'usage_value': 1.352, 'usage_abbr': 'KB', 'extended_storage': '/Amazon S3'}, ]
        view = views.UserIdentificationInformationListView()
        view.get_context_data()
        assert mock_method.called


class TestUserIdentificationInformationListSorted(AdminTestCase):

    def setUp(self):
        self.institution = InstitutionFactory()
        self.users = []
        self.users.append(self.add_user())
        self.users.append(self.add_user())

        self.users[0].is_superuser = True
        self.users[1].is_superuser = True

        self.users[0].add_addon('s3')
        self.user_settings = self.users[0].get_addon('s3')
        self.external_account2 = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings.owner.external_accounts.add(self.external_account2)
        self.user_settings.owner.save()
        self.S3Node_settings2 = S3NodeSettingsFactory(user_settings=self.user_settings)

    def add_user(self):
        user = AuthUserFactory()
        user.save()
        return user

    def view_get(self, url_params):
        request = RequestFactory().get('/fake_path?{}'.format(url_params))
        view = setup_user_view(views.UserIdentificationListView(), request, user=self.users[0])
        return view.get(request)

    def test_get_order_by_fullname_asc(self):
        expected = sorted(map(lambda u: u.fullname, self.users), reverse=False)
        response = self.view_get('order_by=fullname&status=asc')
        list_map = list(map(itemgetter('fullname'), response.context_data['users']))

        result = []
        for i in range(len(list_map) - 1):
            result.append(list_map[i])
        nt.assert_equal(result, expected)

    def test_get_order_without_order_by(self):
        expected = sorted(map(lambda u: u.fullname, self.users), reverse=True)
        response = self.view_get('order_by=&status=desc')
        list_map = list(map(itemgetter('fullname'), response.context_data['users']))
        nt.assert_is_instance(expected, list)
        nt.assert_is_instance(list_map, list)

    def test_get_order_without_status(self):
        expected = sorted(map(lambda u: u.fullname, self.users), reverse=True)
        response = self.view_get('order_by=fullname&status=')
        list_map = list(map(itemgetter('fullname'), response.context_data['users']))
        nt.assert_is_instance(expected, list)
        nt.assert_is_instance(list_map, list)


class TestUserIdentificationListView(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory(fullname='Test User1')
        self.user2 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user3 = AuthUserFactory(fullname='Test User3')
        self.user.is_superuser = False
        self.user2.is_superuser = True
        self.user3.is_staff = True

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
        view = views.UserIdentificationListView()
        view = setup_view(view, self.request)
        results = view.get_user_list()

        for i in range(len(results)):
            list_name.append(results[i]['fullname'])

        nt.assert_equal(len(results), 2)
        nt.assert_in(self.user2.fullname, list_name)
        nt.assert_in(self.user.fullname, list_name)

    def test_get_userlist_user_is_superuser(self):
        self.request.user = self.user2
        view = views.UserIdentificationListView()
        view = setup_view(view, self.request)
        results = view.get_user_list()

        nt.assert_is_instance(results, list)

    def test_get_userlist_permission_denied(self):
        self.request.user = self.user3
        view = views.UserIdentificationListView()
        view = setup_view(view, self.request)
        with nt.assert_raises(Http404):
            view.get_user_list()

    def test_get_userlist_search_guid(self):
        request = RequestFactory().get(reverse('user_identification_information:user_identification_list'),
                                       {'guid': self.user2._id})
        request.user = self.user2
        view = views.UserIdentificationListView()
        view = setup_view(view, request)
        res = view.get_user_list()
        nt.assert_equal(res[0]['id'], self.user2._id)
        nt.assert_equal(len(res), 1)

    def test_get_userlist_search_user_name(self):
        request = RequestFactory().get(reverse('user_identification_information:user_identification_list'),
                                       {'username': self.user2.username})
        request.user = self.user2
        view = views.UserIdentificationListView()
        view = setup_view(view, request)
        res = view.get_user_list()
        nt.assert_equal(res[0]['email'], self.user2.username)
        nt.assert_equal(len(res), 1)

    def test_get_userlist_search_name(self):
        request = RequestFactory().get(reverse('user_identification_information:user_identification_list'),
                                       {'fullname': 'Broken'})
        request.user = self.user2
        view = views.UserIdentificationListView()
        view = setup_view(view, request)
        res = view.get_user_list()
        nt.assert_equal(res[0]['fullname'], self.user2.fullname)
        nt.assert_equal(len(res), 1)

    def test_get_userlist_search_empty(self):
        request = RequestFactory().get(reverse('user_identification_information:user_identification_list'), {'fullname': ''})
        request.user = self.user2
        view = views.UserIdentificationListView()
        view = setup_view(view, request)
        res = view.get_user_list()
        nt.assert_equal(len(res), 5)

    def test_get_userlist_search_none_in_list(self):
        request = RequestFactory().get(reverse('user_identification_information:user_identification_list'),
                                       {'fullname': 'admin'})
        request.user = self.user2
        view = views.UserIdentificationListView()
        view = setup_view(view, request)
        res = view.get_user_list()
        nt.assert_equal(len(res), 0)


class TestUserIdentificationDetailView(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory(fullname='Test User1')
        self.user2 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user3 = AuthUserFactory(fullname='Test User3')
        self.user.is_superuser = False
        self.user2.is_superuser = True
        self.user3.is_staff = True

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user3

        self.user2.add_addon('s3')
        self.user_settings = self.user2.get_addon('s3')
        self.external_account = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.S3Node_settings = S3NodeSettingsFactory(user_settings=self.user_settings)
        self.S3Node_settings.save()

    def test_get_object_permission_denied(self):
        view = views.UserIdentificationDetailView()
        view = setup_view(view, self.request)
        with nt.assert_raises(Http404):
            view.get_object()

    def test_get_object(self):
        view = views.UserIdentificationDetailView()
        request = RequestFactory().get('/fake_path')
        request.user = self.user2
        view = setup_log_view(view, request, guid=self.user2._id)
        results = view.get_object()
        nt.assert_is_instance(results, dict)


class TestExportFileCSVView(AdminTestCase):
    def setUp(self):
        super(TestExportFileCSVView, self).setUp()
        self.user = AuthUserFactory(fullname='Kenny Michel', username='Kenny@gmail.com')
        self.user2 = AuthUserFactory(fullname='alex queen')
        self.user2.is_superuser = True
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user2.affiliated_institutions.add(self.institution)
        self.user.save()
        self.user2.save()
        self.view = views.ExportFileCSVView()

        self.user2.add_addon('s3')
        self.user_settings2 = self.user2.get_addon('s3')
        self.external_account2 = S3AccountFactory(provider_name='Amazon S3')
        self.user_settings2.owner.external_accounts.add(self.external_account2)
        self.user_settings2.owner.save()
        self.S3Node_settings2 = S3NodeSettingsFactory(user_settings=self.user_settings2)

    def test_get(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        view = setup_view(self.view, request)
        res = view.get(request)

        result = res.content.decode('utf-8')

        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res['content-type'], 'text/csv')

    def test_get_is_super_admin(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user2
        view = setup_view(self.view, request)
        res = view.get(request)

        result = res.content.decode('utf-8')

        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res['content-type'], 'text/csv')
