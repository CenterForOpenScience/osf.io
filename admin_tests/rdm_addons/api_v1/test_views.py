# -*- coding: utf-8 -*-

import json
from nose import tools as nt
from django.test import RequestFactory
from django.http import Http404

from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ExternalAccountFactory,
)


from admin_tests.utilities import setup_user_view
from admin.rdm_addons.api_v1 import views

from admin_tests.rdm_addons import factories as rdm_addon_factories


class TestOAuthView(AdminTestCase):
    def setUp(self):
        super(TestOAuthView, self).setUp()
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
        self.view = views.OAuthView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {
            'external_account_id': self.external_account._id,
            'institution_id': self.rdm_addon_option.institution.id,
        }

    def tearDown(self):
        super(TestOAuthView, self).tearDown()
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
        """統合管理者のログインテスト"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """所属していない機関のユーザのログインテスト"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs['institution_id'] = self.rdm_addon_option.institution.id + 1
        nt.assert_equal(self.view.test_func(), False)
        self.view.kwargs['institution_id'] = self.rdm_addon_option.institution.id

    def test_delete(self, *args, **kwargs):
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_equal(self.user.external_accounts.count(), 1)
        nt.assert_equal(self.rdm_addon_option.external_accounts.count(), 1)
        self.view.delete(self.request, *args, **self.view.kwargs)
        nt.assert_equal(self.user.external_accounts.count(), 0)
        nt.assert_equal(self.rdm_addon_option.external_accounts.count(), 0)

    def test_delete_dummy(self, *args, **kwargs):
        self.view.kwargs['external_account_id'] = self.external_account._id + 'dummy'
        with self.assertRaises(Http404):
            self.view.delete(self.request, *args, **self.view.kwargs)
        self.view.kwargs['external_account_id'] = self.external_account._id

    def test_delete_empty(self, *args, **kwargs):
        self.rdm_addon_option.external_accounts.remove(self.external_account)
        with self.assertRaises(Http404):
            self.view.delete(self.request, *args, **self.view.kwargs)


class TestSettingsView(AdminTestCase):
    def setUp(self):
        super(TestSettingsView, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)

        self.request = RequestFactory().get('/fake_path')
        self.view = views.SettingsView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {
            'addon_name': 'dataverse',
            'institution_id': self.institution.id,
        }

    def tearDown(self):
        super(TestSettingsView, self).tearDown()
        self.user.affiliated_institutions.remove()
        self.user.delete()
        self.institution.delete()

    def test_super_admin_login(self):
        """統合管理者のログインテスト"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """所属していない機関のユーザのログインテスト"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.institution.id + 1}
        nt.assert_equal(self.view.test_func(), False)

    def test_get_dataverse(self, *args, **kwargs):
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 200)
        nt.assert_true('result' in res.content)

    def test_get_dummy_addon(self, *args, **kwargs):
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs['addon_name'] = 'dummy'
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 200)
        self.assertJSONEqual(res.content, {})


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
            'addon_name': self.external_account.provider,
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
        """統合管理者のログインテスト"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """所属していない機関のユーザのログインテスト"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.rdm_addon_option.institution.id + 1}
        nt.assert_equal(self.view.test_func(), False)

    def test_get(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 200)
        content = json.loads(res.content)
        nt.assert_equal(len(content['accounts']), 1)

    def test_post_empty(self, *args, **kwargs):
        self.request = RequestFactory().post(
            '/fake',
            data=json.dumps({}),
            content_type='application/json'
        )
        self.view.kwargs['addon_name'] = 'dummy'
        res = self.view.post(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 400)

    def test_post_fake_s3_account(self, *args, **kwargs):
        self.request = RequestFactory().post(
            '/fake',
            data=json.dumps({'access_key': 'aaa', 'secret_key': 'bbb'}),
            content_type='application/json'
        )
        self.view.kwargs['addon_name'] = 's3'
        res = self.view.post(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 400)
