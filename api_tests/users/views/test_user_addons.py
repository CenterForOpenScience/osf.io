import abc
import re
import pytest

from api.base.settings.defaults import API_BASE

from tests.base import ApiAddonTestCase
from osf_tests.factories import AuthUserFactory

from addons.bitbucket.tests.factories import BitbucketAccountFactory
from addons.box.tests.factories import BoxAccountFactory
from addons.dataverse.tests.factories import DataverseAccountFactory
from addons.dropbox.tests.factories import DropboxAccountFactory
from addons.github.tests.factories import GitHubAccountFactory
from addons.googledrive.tests.factories import GoogleDriveAccountFactory
from addons.mendeley.tests.factories import MendeleyAccountFactory
from addons.owncloud.tests.factories import OwnCloudAccountFactory
from addons.s3.tests.factories import S3AccountFactory
from addons.zotero.tests.factories import ZoteroAccountFactory


class UserAddonListMixin:
    def set_setting_list_url(self):
        self.setting_list_url = f'/{API_BASE}users/{self.user._id}/addons/'

    def test_settings_list_GET_returns_user_settings_if_present(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(self.setting_list_url, auth=self.user.auth)

        if not wrong_type:
            addon_data = res.json['data'][0]
            assert addon_data['attributes']['user_has_auth'] is True
            assert self.node._id in addon_data['links']['accounts'][self.account_id]['nodes_connected'][0]
        if wrong_type:
            assert res.status_code == 200
            assert res.json['data'] == []

    def test_settings_list_GET_returns_none_if_absent(self):
        try:
            if self.user.external_accounts.count():
                self.user.external_accounts.clear()
            self.user.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(self.setting_list_url, auth=self.user.auth)

        addon_data = res.json['data']
        assert addon_data == []

    def test_settings_list_raises_error_if_PUT(self):
        res = self.app.put_json_api(
            self.setting_list_url,
            {'id': self.short_name, 'type': 'user-addons'},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert res.status_code == 405

    def test_settings_list_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(
            self.setting_list_url,
            {'id': self.short_name, 'type': 'user-addons'},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert res.status_code == 405

    def test_settings_list_raises_error_if_DELETE(self):
        res = self.app.delete(self.setting_list_url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_settings_list_raises_error_if_nonauthenticated(self):
        res = self.app.get(self.setting_list_url, expect_errors=True)
        assert res.status_code == 401

    def test_settings_list_user_cannot_view_other_user(self):
        other_user = AuthUserFactory()
        res = self.app.get(self.setting_list_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403


class UserAddonDetailMixin:
    def set_setting_detail_url(self):
        self.setting_detail_url = f'/{API_BASE}users/{self.user._id}/addons/{self.short_name}/'

    def test_settings_detail_GET_returns_user_settings_if_present(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(self.setting_detail_url, auth=self.user.auth, expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data']
            assert addon_data['attributes']['user_has_auth'] is True
            assert self.node._id in addon_data['links']['accounts'][self.account_id]['nodes_connected'][0]
        if wrong_type:
            assert res.status_code == 404

    def test_settings_detail_GET_raises_error_if_absent(self):
        wrong_type = self.should_expect_errors()
        try:
            if self.user.external_accounts.count():
                self.user.external_accounts.clear()
            self.user.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(self.setting_detail_url, auth=self.user.auth, expect_errors=True)

        assert res.status_code == 404
        if not wrong_type:
            assert 'Requested addon not enabled' in res.json['errors'][0]['detail']
        if wrong_type:
            assert re.match(r'Requested addon un(available|recognized)', (res.json['errors'][0]['detail']))

    def test_settings_detail_raises_error_if_PUT(self):
        res = self.app.put_json_api(
            self.setting_detail_url,
            {'id': self.short_name, 'type': 'user-addon-detail'},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert res.status_code == 405

    def test_settings_detail_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(
            self.setting_detail_url,
            {'id': self.short_name, 'type': 'user-addon-detail'},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert res.status_code == 405

    def test_settings_detail_raises_error_if_DELETE(self):
        res = self.app.delete(self.setting_detail_url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_settings_detail_raises_error_if_nonauthenticated(self):
        res = self.app.get(self.setting_detail_url, expect_errors=True)

        assert res.status_code == 401

    def test_settings_detail_user_cannot_view_other_user(self):
        other_user = AuthUserFactory()
        res = self.app.get(self.setting_detail_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403


class UserAddonAccountListMixin:
    def set_account_list_url(self):
        self.account_list_url = f'/{API_BASE}users/{self.user._id}/addons/{self.short_name}/accounts/'

    def test_account_list_GET_returns_accounts_if_present(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(self.account_list_url, auth=self.user.auth, expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data'][0]
            assert addon_data['id'] == self.account._id
            assert addon_data['attributes']['display_name'] == self.account.display_name
            assert addon_data['attributes']['provider'] == self.account.provider
            assert addon_data['attributes']['profile_url'] == self.account.profile_url
        if wrong_type:
            assert res.status_code == 404

    def test_account_list_raises_error_if_absent(self):
        wrong_type = self.should_expect_errors()
        try:
            if self.user.external_accounts.count():
                self.user.external_accounts.clear()
            self.user.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(self.account_list_url, auth=self.user.auth, expect_errors=True)

        assert res.status_code == 404
        if not wrong_type:
            assert 'Requested addon not enabled' in res.json['errors'][0]['detail']
        if wrong_type:
            assert re.match(r'Requested addon un(available|recognized)', (res.json['errors'][0]['detail']))

    def test_account_list_raises_error_if_PUT(self):
        res = self.app.put_json_api(
            self.account_list_url,
            {'id': self.short_name, 'type': 'user-external_accounts'},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert res.status_code == 405

    def test_account_list_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(
            self.account_list_url,
            {'id': self.short_name, 'type': 'user-external_accounts'},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert res.status_code == 405

    def test_account_list_raises_error_if_DELETE(self):
        res = self.app.delete(self.account_list_url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_account_list_raises_error_if_nonauthenticated(self):
        res = self.app.get(self.account_list_url, expect_errors=True)

        assert res.status_code == 401

    def test_account_list_user_cannot_view_other_user(self):
        other_user = AuthUserFactory()
        res = self.app.get(self.account_list_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403


class UserAddonAccountDetailMixin:
    def set_account_detail_url(self):
        self.account_detail_url = '/{}users/{}/addons/{}/accounts/{}/'.format(
            API_BASE, self.user._id, self.short_name, self.account_id
        )

    def test_account_detail_GET_returns_account_if_enabled(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(self.account_detail_url, auth=self.user.auth, expect_errors=wrong_type)

        if not wrong_type:
            addon_data = res.json['data']
            assert addon_data['id'] == self.account._id
            assert addon_data['attributes']['display_name'] == self.account.display_name
            assert addon_data['attributes']['provider'] == self.account.provider
            assert addon_data['attributes']['profile_url'] == self.account.profile_url
        if wrong_type:
            assert res.status_code == 404

    def test_account_detail_raises_error_if_not_found(self):
        wrong_type = self.should_expect_errors()
        try:
            if self.user.external_accounts.count():
                self.user.external_accounts.clear()
            self.user.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(self.account_detail_url, auth=self.user.auth, expect_errors=True)

        assert res.status_code == 404
        if not wrong_type:
            assert 'Requested addon not enabled' in res.json['errors'][0]['detail']
        if wrong_type:
            assert re.match(r'Requested addon un(available|recognized)', (res.json['errors'][0]['detail']))

    def test_account_detail_raises_error_if_PUT(self):
        res = self.app.put_json_api(
            self.account_detail_url,
            {'id': self.short_name, 'type': 'user-external_account-detail'},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert res.status_code == 405

    def test_account_detail_raises_error_if_PATCH(self):
        res = self.app.patch_json_api(
            self.account_detail_url,
            {'id': self.short_name, 'type': 'user-external_account-detail'},
            auth=self.user.auth,
            expect_errors=True,
        )
        assert res.status_code == 405

    def test_account_detail_raises_error_if_DELETE(self):
        res = self.app.delete(self.account_detail_url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_account_detail_raises_error_if_nonauthenticated(self):
        res = self.app.get(self.account_detail_url, expect_errors=True)

        assert res.status_code == 401

    def test_account_detail_user_cannot_view_other_user(self):
        other_user = AuthUserFactory()
        res = self.app.get(self.account_detail_url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 403


class UserAddonTestSuiteMixin(
    UserAddonListMixin, UserAddonDetailMixin, UserAddonAccountListMixin, UserAddonAccountDetailMixin
):
    def set_urls(self):
        self.set_setting_list_url()
        self.set_setting_detail_url()
        self.set_account_list_url()
        self.set_account_detail_url()

    def should_expect_errors(self, success_types=('OAUTH',)):
        return self.addon_type not in success_types


class UserOAuthAddonTestSuiteMixin(UserAddonTestSuiteMixin):
    addon_type = 'OAUTH'

    @property
    @abc.abstractmethod
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


# OAUTH


class TestUserBitbucketAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'bitbucket'
    AccountFactory = BitbucketAccountFactory


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


class TestUserOwnCloudAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'owncloud'
    AccountFactory = OwnCloudAccountFactory


@pytest.mark.skip('Unskip when figshare v2 addon is ported')
class TestUserFigshareAddon(UserOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'figshare'
    # AccountFactory = FigshareAccountFactory


class TestUserInvalidAddon(UserAddonTestSuiteMixin, ApiAddonTestCase):
    addon_type = 'INVALID'
    short_name = 'fake'
