# -*- coding: utf-8 -*-
from nose import tools as nt

from django.test import RequestFactory
from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory


from admin.rdm_announcement.forms import PreviewForm, SettingsForm
from osf.models.rdm_announcement import RdmAnnouncementOption
from admin.rdm_announcement import views
from admin_tests.utilities import setup_user_view
from admin_tests.rdm_announcement.test_forms import data

option_data = dict(
    twitter_api_key='VROOrgA0ZLI6gVe7V0H3TDmAU',
    twitter_api_secret='OOax8MP5ErHlTNMcbTUs9kWP3I2x59wZvZBCvxjvBFTnmGH6pd',
    twitter_access_token='934705515824758784-1eicHz46WnTPzn5XQqnbiA8dl4yvIka',
    twitter_access_token_secret='vkc0WgE0S5jodaoq8l9SBQIZCyvWI8Aowb1qZRIAktBA7',
    facebook_api_key='935938406547385',
    facebook_api_secret='f15fccd3b67d437b73ee43b8f629c408',
    facebook_access_token='EAACvJ14jcSsBAIujVKBHWZCo4xBVRCZAva3ypbEfaQuOmyxOQAY9FZBJyqs6wyF2lwRIzGuieXZAzLMezutqJaTT9khOajkqZCYlVQCQpnnczBt6L7rgAZBQJZAHoAOHDjZAljARtp2p7sezXqYpZAZANM9IBVnWMYBClfcN7pxbrZAB5myw7eyeTYi',
    redmine_api_url='http://localhost:3000/projects/test-project/issues.json',
    redmine_api_key='54367a4c8a859b5db74e4c3f2c17b35824c559ec',
)


class TestIndexView(AdminTestCase):

    def setUp(self):
        super(TestIndexView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.IndexView()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def tearDown(self):
        super(TestIndexView, self).tearDown()
        self.user.delete()

    def test_super_admin_login(self, *args, **kwargs):
        """統合管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_super_admin_get(self, *args, **kwargs):
        """統合管理者のgetメソッドのテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_admin_get(self, *args, **kwargs):
        """機関管理者のgetメソッドのテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_get_context_data(self):
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['form'], PreviewForm)

    def test_post_option_check_okay(self):
        mod_data = dict(option_data)
        mod_data.update({'user_id': self.user.id})
        test_option = RdmAnnouncementOption.objects.create(**mod_data)
        test_option.save()
        self.form = PreviewForm(data)
        ret = self.view.option_check(data)
        nt.assert_is_instance(test_option, RdmAnnouncementOption)
        nt.assert_true(self.form.is_valid())
        nt.assert_true(ret)

    def test_post_option_check_raise(self):
        mod_data = dict(option_data)
        mod_data.update({'user_id': self.user.id, 'twitter_api_key': None})
        test_option = RdmAnnouncementOption.objects.create(**mod_data)
        test_option.save()
        mod_data2 = dict(data)
        mod_data2.update({'announcement_type': 'SNS (Twitter)'})
        self.form = PreviewForm(mod_data2)
        ret = self.view.option_check(mod_data2)
        nt.assert_is_instance(test_option, RdmAnnouncementOption)
        nt.assert_true(self.form.is_valid())
        nt.assert_false(ret)

    def test_post_option_check_raise2(self):
        mod_data = dict(option_data)
        mod_data.update({'user_id': self.user.id, 'facebook_api_key': None})
        test_option = RdmAnnouncementOption.objects.create(**mod_data)
        test_option.save()
        mod_data2 = dict(data)
        mod_data2.update({'announcement_type': 'SNS (Facebook)'})
        self.form = PreviewForm(mod_data2)
        ret = self.view.option_check(mod_data2)
        nt.assert_is_instance(test_option, RdmAnnouncementOption)
        nt.assert_true(self.form.is_valid())
        nt.assert_false(ret)


class TestSettingsView(AdminTestCase):
    def setUp(self):
        super(TestSettingsView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.SettingsView()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def tearDown(self):
        super(TestSettingsView, self).tearDown()
        self.user.delete()

    def test_super_admin_login(self, *args, **kwargs):
        """統合管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_super_admin_get(self, *args, **kwargs):
        """統合管理者のgetメソッドのテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_admin_get(self, *args, **kwargs):
        """機関管理者のgetメソッドのテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_get_context_data(self):
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['form'], SettingsForm)

    def test_get_exist_option_set(self):
        """統合管理者のテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        new_user = AuthUserFactory()
        new_user.is_active = True
        new_user.is_registered = True
        new_user.is_superuser = True
        new_user.is_staff = True
        mod_data = dict(option_data)
        mod_data.update({'user_id': new_user.id})
        new_user_option = RdmAnnouncementOption.objects.create(**mod_data)
        new_user_option.save()
        ret = self.view.get_exist_option_set()
        nt.assert_is_instance(new_user_option, RdmAnnouncementOption)
        nt.assert_true(ret)

    def test_get_exist_option_set2(self):
        """機関管理者のテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        new_user = AuthUserFactory()
        new_user.is_active = True
        new_user.is_registered = True
        new_user.is_superuser = False
        new_user.is_staff = True
        mod_data = dict(option_data)
        mod_data.update({'user_id': new_user.id})
        new_user_option = RdmAnnouncementOption.objects.create(**mod_data)
        new_user_option.save()
        ret = self.view.get_exist_option_set()
        nt.assert_is_instance(new_user_option, RdmAnnouncementOption)
        nt.assert_true(ret)

    def test_get_exist_option_set3(self):
        """統合管理者でも機関管理者でもないユーザのテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        new_user = AuthUserFactory()
        new_user.is_active = True
        new_user.is_registered = True
        new_user.is_superuser = False
        new_user.is_staff = False
        mod_data = dict(option_data)
        mod_data.update({'user_id': new_user.id})
        new_user_option = RdmAnnouncementOption.objects.create(**mod_data)
        new_user_option.save()
        ret = self.view.get_exist_option_set()
        nt.assert_is_instance(new_user_option, RdmAnnouncementOption)
        nt.assert_equal(ret, 'False')

class TestSettingsUpdateView(AdminTestCase):
    def setUp(self):
        super(TestSettingsUpdateView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.SettingsUpdateView()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def tearDown(self):
        super(TestSettingsUpdateView, self).tearDown()
        self.user.delete()

    def test_super_admin_login(self, *args, **kwargs):
        """統合管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

class TestSendView(AdminTestCase):
    def setUp(self):
        super(TestSendView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.SendView()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def tearDown(self):
        super(TestSendView, self).tearDown()
        self.user.delete()

    def test_super_admin_login(self, *args, **kwargs):
        """統合管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)
