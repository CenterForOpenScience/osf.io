# -*- coding: utf-8 -*-

import flask
from nose import tools as nt
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ExternalAccountFactory,
    MockOAuth2Provider,
)


from admin_tests.utilities import setup_user_view
from admin.rdm_addons.oauth import views

from admin_tests.rdm_addons import factories as rdm_addon_factories

from website.routes import make_url_map


def add_session_to_request(request):
    """Annotate a request object with a session"""
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()

class TestConnectView(AdminTestCase):
    def setUp(self):
        super(TestConnectView, self).setUp()
        self.user = AuthUserFactory()
        self.external_account = ExternalAccountFactory()
        self.institution = InstitutionFactory()

        self.user.affiliated_institutions.add(self.institution)

        self.provider = MockOAuth2Provider(self.external_account)

        self.request = RequestFactory().get('/fake_path')
        add_session_to_request(self.request)
        self.view = views.ConnectView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {
            'addon_name': self.external_account.provider,
            'institution_id': self.institution.id,
        }

    def tearDown(self):
        super(TestConnectView, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution)
        self.user.delete()
        self.institution.delete()
        self.external_account.delete()

    def test_super_admin_login(self):
        """login test at superuser"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """login test at institution administrator"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """login test at user not superuser or institution administrator"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """login test at invalid user"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """login test at unregistered user"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """login test at user unorganized institution"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.institution.id + 1}
        nt.assert_equal(self.view.test_func(), False)

    def test_get(self, *args, **kwargs):
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 302)

class TestCallbackView(AdminTestCase):
    def setUp(self):
        super(TestCallbackView, self).setUp()
        self.user = AuthUserFactory()
        self.external_account = ExternalAccountFactory()
        self.institution = InstitutionFactory()

        self.provider = MockOAuth2Provider(self.external_account)

        self.user.affiliated_institutions.add(self.institution)

        app = flask.Flask(__name__)
        make_url_map(app)
        app.config['SECRET_KEY'] = 'aaaaa'
        self.ctx = app.test_request_context()
        self.ctx.push()

        self.request = RequestFactory().get('/fake_path')
        add_session_to_request(self.request)
        self.view0 = views.ConnectView()
        self.view0 = setup_user_view(self.view0, self.request, user=self.user)
        self.view0.kwargs = {
            'addon_name': self.external_account.provider,
            'institution_id': self.institution.id,
        }

        self.view = views.CallbackView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {
            'addon_name': self.external_account.provider,
            'institution_id': self.institution.id,
        }

    def tearDown(self):
        super(TestCallbackView, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution)
        self.user.delete()
        self.institution.delete()
        self.external_account.delete()
        try:
            self.ctx.pop()
        except AssertionError:
            pass

    def test_super_admin_login(self):
        """login test at superuser"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """login test at institution administrator"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """login test at user not superuser or institution administrator"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """login test at invalid user"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """login test at unregistered user"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)


class TestCompleteView(AdminTestCase):
    def setUp(self):
        super(TestCompleteView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.CompleteView()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def tearDown(self):
        super(TestCompleteView, self).tearDown()
        self.user.delete()

    def test_login(self):
        """login test"""
        nt.assert_true(self.view.test_func())

    def test_get_context_data(self, *args, **kwargs):
        res = views.CompleteView.as_view()(self.request)
        nt.assert_equal(res.status_code, 200)


class TestAccountsView(AdminTestCase):
    def setUp(self):
        super(TestAccountsView, self).setUp()
        self.user = AuthUserFactory()
        self.external_account = ExternalAccountFactory()

        self.rdm_addon_option = rdm_addon_factories.RdmAddonOptionFactory()
        self.rdm_addon_option.provider = self.external_account.provider
        self.rdm_addon_option.external_accounts.add(self.external_account)
        self.rdm_addon_option.save()

        self.user.affiliated_institutions.add(self.rdm_addon_option.institution)
        self.user.external_accounts.add(self.external_account)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.AccountsView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {
            'external_account_id': self.external_account._id,
            'institution_id': self.rdm_addon_option.institution.id,
        }

    def tearDown(self):
        super(TestAccountsView, self).tearDown()
        institution = self.rdm_addon_option.institution
        self.user.affiliated_institutions.remove(institution)
        if self.user.external_accounts.filter(pk=self.external_account.id).exists():
            self.user.external_accounts.remove(self.external_account)
        self.user.delete()
        if self.rdm_addon_option.external_accounts.filter(pk=self.external_account.id).exists():
            self.rdm_addon_option.external_accounts.remove(self.external_account)
        self.rdm_addon_option.delete()
        institution.delete()
        self.external_account.delete()

    def test_super_admin_login(self):
        """login test at superuser"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """login test at institution administrator"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """login test at user not superuser or institution administrator"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """login test at invalid user"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """login test at unregistered user"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """login test at user unorganized institution"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.rdm_addon_option.institution.id + 1}
        nt.assert_equal(self.view.test_func(), False)

    def test_delete(self, *args, **kwargs):
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_equal(self.user.external_accounts.count(), 1)
        nt.assert_equal(self.rdm_addon_option.external_accounts.count(), 1)


'''
    def test_delete_dummy(self, *args, **kwargs):
        self.view.kwargs['external_account_id'] = self.external_account._id + 'dummy'
        with self.assertRaises(Http404):
            res = self.view.delete(self.request, *args, **self.view.kwargs)
        self.view.kwargs['external_account_id'] = self.external_account._id

    def test_delete_empty(self, *args, **kwargs):
        self.rdm_addon_option.external_accounts.remove(self.external_account)
        with self.assertRaises(Http404):
            res = self.view.delete(self.request, *args, **self.view.kwargs)
'''
