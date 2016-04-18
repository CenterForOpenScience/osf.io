# -*- coding: utf-8 -*-
import abc
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiAddonTestCase

from website.addons.box.tests.factories import BoxAccountFactory

class UserAddonListMixin(object):
    def set_setting_list_url(self):
        self.setting_list_url = '/{}users/{}/addons/'.format(
            API_BASE, self.user._id
        )

    def test_settings_list_GET_returns_user_settings_if_present(self):
        pass

    def test_settings_list_GET_returns_none_if_absent(self):
        pass

    def test_settings_list_raises_error_if_not_GET(self):
        pass

    def test_settings_list_raises_error_if_nonauthenticated(self):
        pass

    def test_settings_list_user_cannot_view_other_user(self):
        pass


class UserAddonDetailMixin(object):
    def set_setting_detail_url(self):
        self.setting_detail_url = '/{}users/{}/addons/{}/'.format(
            API_BASE, self.user._id, self.short_name
        )

    def test_settings_detail_GET_returns_user_settings_if_present(self):
        pass

    def test_settings_detail_GET_returns_none_if_absent(self):
        pass

    def test_settings_detail_raises_error_if_not_GET(self):
        pass

    def test_settings_detail_raises_error_if_nonauthenticated(self):
        pass

    def test_settings_detail_user_cannot_view_other_user(self):
        pass


class UserAddonAccountListMixin(object):
    def set_account_list_url(self):
        self.account_list_url = '/{}users/{}/addons/{}/accounts/'.format(
            API_BASE, self.user._id, self.short_name
        )

    def test_account_list_GET_returns_accounts_if_present(self):
        pass

    def test_account_list_returns_none_if_absent(self):
        pass

    def test_account_list_raises_error_if_not_GET(self):
        pass

    def test_account_list_raises_error_if_nonauthenticated(self):
        pass

    def test_account_list_user_cannot_view_other_user(self):
        pass


class UserAddonAccountDetailMixin(object):
    def set_account_detail_url(self):
        self.account_detail_url = '/{}users/{}/addons/{}/accounts/{}'.format(
            API_BASE, self.user._id, self.short_name,
            self.account._id if self.account else ''
        )

    def test_account_detail_GET_returns_account_if_enabled(self):
        pass

    def test_account_detail_raises_error_if_not_found(self):
        pass

    def test_account_detail_raises_error_if_not_GET(self):
        pass

    def test_account_detail_raises_error_if_nonauthenticated(self):
        pass

    def test_account_detail_user_cannot_view_other_user(self):
        pass

class UserAddonTestSuiteMixin(UserAddonListMixin, UserAddonDetailMixin, UserAddonAccountListMixin, UserAddonAccountDetailMixin):
    def set_urls(self):
        self.set_setting_list_url()
        self.set_setting_detail_url()
        self.set_account_list_url()
        self.set_account_detail_url()


class UserOAuthAddonTestSuiteMixin(UserAddonTestSuiteMixin):
    addon_type = 'OAUTH'


class TestUserBoxAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'box'
    AccountFactory = BoxAccountFactory

    def setUp(self):
        super(TestUserBoxAddon, self).setUp()
        self.set_urls()

