# -*- coding: utf-8 -*-
import abc
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiAddonTestCase
from tests.factories import AuthUserFactory
from tests.utils import mock_auth

from website.addons.box.tests.factories import BoxAccountFactory
from website.addons.dataverse.tests.factories import DataverseAccountFactory
from website.addons.dropbox.tests.factories import DropboxAccountFactory
from website.addons.github.tests.factories import GitHubAccountFactory
from website.addons.googledrive.tests.factories import GoogleDriveAccountFactory
from website.addons.mendeley.tests.factories import MendeleyAccountFactory
from website.addons.s3.tests.factories import S3AccountFactory
from website.addons.zotero.tests.factories import ZoteroAccountFactory

class UserAddonListMixin(object):
    def set_setting_list_url(self):
        self.setting_list_url = '/{}users/{}/addons/'.format(
            API_BASE, self.user._id
        )

    def test_settings_list_GET_returns_user_settings_if_present(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_list_url,
            auth=self.user.auth)

        if not wrong_type:
            addon_data = res.json['data'][0]
            assert_true(addon_data['attributes']['user_has_auth'])
            assert_in(self.node._id, addon_data['links']['accounts'][self.account_id]['nodes_connected'][0])
        if wrong_type:
            assert_equal(res.status_code, 200)
            assert_equal(res.json['data'], [])

    def test_settings_list_GET_returns_none_if_absent(self):
        try:
            if self.user.external_accounts:
                self.user.external_accounts.pop()
            self.user.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.setting_list_url,
            auth=self.user.auth)

        addon_data = res.json['data']
        assert_equal(addon_data, [])

    def test_settings_list_raises_error_if_PUT(self):
        res = self.app.put_json_api(self.setting_list_url, {
            'id': self.short_name,
            'type': 'user-addons'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_settings_list_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(self.setting_list_url, {
            'id': self.short_name,
            'type': 'user-addons'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_settings_list_raises_error_if_DELETE(self):
        res = self.app.delete(
            self.setting_list_url,
            auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_settings_list_raises_error_if_nonauthenticated(self):
        res = self.app.get(
            self.setting_list_url,
            expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_settings_list_user_cannot_view_other_user(self):
        other_user = AuthUserFactory()
        res = self.app.get(
            self.setting_list_url,
            auth=other_user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)


class UserAddonDetailMixin(object):
    def set_setting_detail_url(self):
        self.setting_detail_url = '/{}users/{}/addons/{}/'.format(
            API_BASE, self.user._id, self.short_name
        )

    def test_settings_detail_GET_returns_user_settings_if_present(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data']
            assert_true(addon_data['attributes']['user_has_auth'])
            assert_in(self.node._id, addon_data['links']['accounts'][self.account_id]['nodes_connected'][0])
        if wrong_type:
            assert_equal(res.status_code, 404)

    def test_settings_detail_GET_raises_error_if_absent(self):
        wrong_type = self.should_expect_errors()
        try:
            if self.user.external_accounts:
                self.user.external_accounts.pop()
            self.user.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=True)

        assert_equal(res.status_code, 404)
        if not wrong_type:
            assert_in('Requested addon not enabled', res.json['errors'][0]['detail'])
        if wrong_type:
            assert_in('Requested addon unavailable', res.json['errors'][0]['detail'])

    def test_settings_detail_raises_error_if_PUT(self):
        res = self.app.put_json_api(self.setting_detail_url, {
            'id': self.short_name,
            'type': 'user-addon-detail'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_settings_detail_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(self.setting_detail_url, {
            'id': self.short_name,
            'type': 'user-addon-detail'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_settings_detail_raises_error_if_DELETE(self):
        res = self.app.delete(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_settings_detail_raises_error_if_nonauthenticated(self):
        res = self.app.get(
            self.setting_detail_url,
            expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_settings_detail_user_cannot_view_other_user(self):
        other_user = AuthUserFactory()
        res = self.app.get(
            self.setting_detail_url,
            auth=other_user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)


class UserAddonAccountListMixin(object):
    def set_account_list_url(self):
        self.account_list_url = '/{}users/{}/addons/{}/accounts/'.format(
            API_BASE, self.user._id, self.short_name
        )

    def test_account_list_GET_returns_accounts_if_present(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.account_list_url,
            auth=self.user.auth,
            expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data'][0]
            assert_equal(addon_data['id'], self.account._id)
            assert_equal(addon_data['attributes']['display_name'], self.account.display_name)
            assert_equal(addon_data['attributes']['provider'], self.account.provider)
            assert_equal(addon_data['attributes']['profile_url'], self.account.profile_url)
        if wrong_type:
            assert_equal(res.status_code, 404)

    def test_account_list_raises_error_if_absent(self):
        wrong_type = self.should_expect_errors()
        try:
            if self.user.external_accounts:
                self.user.external_accounts.pop()
            self.user.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.account_list_url,
            auth=self.user.auth,
            expect_errors=True)

        assert_equal(res.status_code, 404)
        if not wrong_type:
            assert_in('Requested addon not enabled', res.json['errors'][0]['detail'])
        if wrong_type:
            assert_in('Requested addon unavailable', res.json['errors'][0]['detail'])

    def test_account_list_raises_error_if_PUT(self):
        res = self.app.put_json_api(self.account_list_url, {
            'id': self.short_name,
            'type': 'user-external_accounts'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_account_list_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(self.account_list_url, {
            'id': self.short_name,
            'type': 'user-external_accounts'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_account_list_raises_error_if_DELETE(self):
        res = self.app.delete(
            self.account_list_url,
            auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_account_list_raises_error_if_nonauthenticated(self):
        res = self.app.get(
            self.account_list_url,
            expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_account_list_user_cannot_view_other_user(self):
        other_user = AuthUserFactory()
        res = self.app.get(
            self.account_list_url,
            auth=other_user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)


class UserAddonAccountDetailMixin(object):
    def set_account_detail_url(self):
        self.account_detail_url = '/{}users/{}/addons/{}/accounts/{}/'.format(
            API_BASE, self.user._id, self.short_name, self.account_id
        )

    def test_account_detail_GET_returns_account_if_enabled(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.account_detail_url,
            auth=self.user.auth,
            expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data']
            assert_equal(addon_data['id'], self.account._id)
            assert_equal(addon_data['attributes']['display_name'], self.account.display_name)
            assert_equal(addon_data['attributes']['provider'], self.account.provider)
            assert_equal(addon_data['attributes']['profile_url'], self.account.profile_url)
        if wrong_type:
            assert_equal(res.status_code, 404)

    def test_account_detail_raises_error_if_not_found(self):
        wrong_type = self.should_expect_errors()
        try:
            if self.user.external_accounts:
                self.user.external_accounts.pop()
            self.user.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.account_detail_url,
            auth=self.user.auth,
            expect_errors=True)

        assert_equal(res.status_code, 404)
        if not wrong_type:
            assert_in('Requested addon not enabled', res.json['errors'][0]['detail'])
        if wrong_type:
            assert_in('Requested addon unavailable', res.json['errors'][0]['detail'])

    def test_account_detail_raises_error_if_PUT(self):
        res = self.app.put_json_api(self.account_detail_url, {
            'id': self.short_name,
            'type': 'user-external_account-detail'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_account_detail_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(self.account_detail_url, {
            'id': self.short_name,
            'type': 'user-external_account-detail'
            }, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_account_detail_raises_error_if_DELETE(self):
        res = self.app.delete(
            self.account_detail_url,
            auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 405)

    def test_account_detail_raises_error_if_nonauthenticated(self):
        res = self.app.get(
            self.account_detail_url,
            expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_account_detail_user_cannot_view_other_user(self):
        other_user = AuthUserFactory()
        res = self.app.get(
            self.account_detail_url,
            auth=other_user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)

class UserAddonTestSuiteMixin(UserAddonListMixin, UserAddonDetailMixin, UserAddonAccountListMixin, UserAddonAccountDetailMixin):
    def set_urls(self):
        self.set_setting_list_url()
        self.set_setting_detail_url()
        self.set_account_list_url()
        self.set_account_detail_url()

    def should_expect_errors(self, success_types=('OAUTH', )):
        return self.addon_type not in success_types

class UserOAuthAddonTestSuiteMixin(UserAddonTestSuiteMixin):
    addon_type = 'OAUTH'

    @abc.abstractproperty
    def AccountFactory(self):
        pass


class UserUnmanageableAddonTestSuiteMixin(UserAddonTestSuiteMixin):
    addon_type = 'UNMANAGEABLE'

# UNMANAGEABLE

class TestUserForwardAddon(UserUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'forward'


class TestUserOsfStorageAddon(UserUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'osfstorage'


class TestUserTwoFactorAddon(UserUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'twofactor'


class TestUserWikiAddon(UserUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'wiki'


class TestUserFigshareAddon(UserUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'figshare'


# OAUTH


class TestUserBoxAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'box'
    AccountFactory = BoxAccountFactory


class TestUserDataverseAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'dataverse'
    AccountFactory = DataverseAccountFactory


class TestUserDropboxAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'dropbox'
    AccountFactory = DropboxAccountFactory


class TestUserGitHubAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'github'
    AccountFactory = GitHubAccountFactory


class TestUserGoogleDriveAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'googledrive'
    AccountFactory = GoogleDriveAccountFactory


class TestUserMendeleyAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'mendeley'
    AccountFactory = MendeleyAccountFactory


class TestUserS3Addon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 's3'
    AccountFactory = S3AccountFactory


class TestUserZoteroAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'zotero'
    AccountFactory = ZoteroAccountFactory


class TestUserInvalidAddon(UserAddonTestSuiteMixin, ApiAddonTestCase):
    addon_type = 'INVALID'
    short_name = 'fake'
