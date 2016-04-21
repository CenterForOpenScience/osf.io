# -*- coding: utf-8 -*-
import abc
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth

from tests.base import ApiAddonTestCase
from tests.factories import AuthUserFactory
from website.addons.box.tests.factories import BoxAccountFactory, BoxNodeSettingsFactory
from website.addons.dataverse.tests.factories import DataverseAccountFactory, DataverseNodeSettingsFactory
from website.addons.dropbox.tests.factories import DropboxAccountFactory, DropboxNodeSettingsFactory
from website.addons.github.tests.factories import GitHubAccountFactory, GitHubNodeSettingsFactory
from website.addons.googledrive.tests.factories import GoogleDriveAccountFactory, GoogleDriveNodeSettingsFactory
from website.addons.mendeley.tests.factories import MendeleyAccountFactory, MendeleyNodeSettingsFactory
from website.addons.s3.tests.factories import S3AccountFactory, S3NodeSettingsFactory
from website.addons.zotero.tests.factories import ZoteroAccountFactory, ZoteroNodeSettingsFactory


class NodeAddonListMixin(object):
    def set_setting_list_url(self):
        self.setting_list_url = '/{}nodes/{}/addons/?page[size]=100'.format(
            API_BASE, self.node._id
        )

    def get_response_for_addon(self, response):
        for datum in response.json['data']:
            if datum['id'] == self.short_name:
                return datum['attributes']
        return None

    def test_settings_list_GET_enabled(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_list_url,
            auth=self.user.auth)

        addon_data = self.get_response_for_addon(res)
        if not wrong_type:
            assert_equal(self.account._id, addon_data['auth_id'])
            assert_equal(self.node._id, addon_data['node'])
            assert_equal(self.node_settings.has_auth, addon_data['has_auth'])
            assert_equal(self.node_settings.folder_id, addon_data['folder'])
        if wrong_type:
            assert_equal(addon_data, None)

    def test_settings_list_GET_disabled(self):
        wrong_type = self.should_expect_errors()
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.setting_list_url,
            auth=self.user.auth,
            expect_errors=wrong_type)
        addon_data = self.get_response_for_addon(res)
        if not wrong_type:
            assert_equal(addon_data['auth_id'], None)
            assert_equal(addon_data['node'], None)
            assert_false(addon_data['has_auth'])
        if wrong_type:
            assert_equal(addon_data, None)        

    def test_settings_list_raises_error_if_not_GET(self):
        put_res = self.app.put_json_api(self.setting_list_url, {
            'id': self.short_name,
            'type': 'node-addons',
            'enabled': False
            }, auth=self.user.auth,
            expect_errors=True)
        patch_res = self.app.patch_json_api(self.setting_list_url, {
            'id': self.short_name,
            'type': 'node-addons',
            'enabled': False
            }, auth=self.user.auth,
            expect_errors=True)
        del_res = self.app.delete(
            self.setting_list_url,
            auth=self.user.auth,
            expect_errors=True)
        assert_equal(put_res.status_code, 405)
        assert_equal(patch_res.status_code, 405)
        assert_equal(del_res.status_code, 405)

    def test_settings_list_raises_error_if_noncontrib_not_public(self):
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_list_url,
            auth=noncontrib.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_settings_list_noncontrib_public_can_view(self):
        self.node.set_privacy('public', auth=self.auth)
        wrong_type = self.should_expect_errors()
        noncontrib = AuthUserFactory()
        res = self.app.get(
            self.setting_list_url,
            auth=noncontrib.auth)
        addon_data = self.get_response_for_addon(res)
        if not wrong_type:
            assert_equal(self.account._id, addon_data['auth_id'])
            assert_equal(self.node._id, addon_data['node'])
            assert_equal(self.node_settings.has_auth, addon_data['has_auth'])
            assert_equal(self.node_settings.folder_id, addon_data['folder'])
        if wrong_type:
            assert_equal(addon_data, None)

class NodeAddonDetailMixin(object):
    def set_setting_detail_url(self):
        self.setting_detail_url = '/{}nodes/{}/addons/{}/'.format(
            API_BASE, self.node._id, self.short_name
        )

    def test_settings_detail_GET_enabled(self):
        wrong_type = self.should_expect_errors()
        res = self.app.get(
            self.setting_detail_url,
            auth=self.user.auth)

        addon_data = self.get_response_for_addon(res)
        if not wrong_type:
            assert_equal(self.account._id, addon_data['auth_id'])
            assert_equal(self.node._id, addon_data['node'])
            assert_equal(self.node_settings.has_auth, addon_data['has_auth'])
            assert_equal(self.node_settings.folder_id, addon_data['folder'])
        if wrong_type:
            assert_equal(addon_data, None)

    def test_settings_detail_GET_disabled(self):
        wrong_type = self.should_expect_errors()
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.get(
            self.setting_detail_url,
            auth=self.user.auth,
            expect_errors=wrong_type)
        addon_data = res.json['data'].get('attributes', None)
        if not wrong_type:
            assert_equal(addon_data['auth_id'], None)
            assert_equal(addon_data['node'], None)
            assert_false(addon_data['has_auth'])
        if wrong_type:
            assert_equal(addon_data, None)

    def test_settings_detail_PUT_all_sets(self):
        wrong_type = self.should_expect_errors()
        try:
            self.node.delete_addon(self.short_name, auth=self.auth)
        except ValueError:
            # If addon was mandatory -- OSFStorage
            pass
        res = self.app.put_json_api(self.setting_detail_url, 
            {'data': { 
                'id': self.short_name,
                'type': 'node_addons',
                'attributes': {
                    'auth_id': self.account._id,
                    'folder': '1234567890',
                    'enabled': True
                    }
                }
            }, auth=self.user.auth,
            expect_errors=wrong_type)
        if not wrong_type:
            addon_data = res.json['data']['attributes']
            assert_equal(addon_data['auth_id'], self.account._id)
            assert_equal(addon_data['node'], self.node._id)
            assert_equal(addon_data['folder'], '1234567890')
            assert_true(addon_data['has_auth'])
        if wrong_type:
            assert_equal(res.status_code, 405)


    def test_settings_detail_PUT_none_disables(self):
        pass

    def test_settings_detail_PATCH_toggles_enabled_disabled(self):
        pass

    def test_settings_detail_PATCH_readcontrib_raises_error(self):
        pass

    def test_settings_detail_raises_error_if_DELETE_or_POST(self):
        pass

    def test_settings_detail_raises_error_if_noncontrib_not_public_GET(self):
        pass

    def test_settings_detail_raises_error_if_noncontrib_not_public_PUT(self):
        pass

    def test_settings_detail_raises_error_if_noncontrib_not_public_PATCH(self):
        pass

    def test_settings_detail_noncontrib_public_can_view(self):
        pass

    def test_settings_detail_noncontrib_public_cannot_edit(self):
        pass


class NodeAddonFolderMixin(object):
    def set_folder_url(self):
        self.folder_url = '/{}/nodes/{}/addons/{}/folders/'.format(
            API_BASE, self.node._id, self.short_name
        )

    def test_folder_list_GET_expected_behavior(self):
        pass


class NodeAddonTestSuiteMixin(NodeAddonListMixin, NodeAddonDetailMixin, NodeAddonFolderMixin):
    def set_urls(self):
        self.set_setting_list_url()
        self.set_setting_detail_url()
        self.set_folder_url()

    def should_expect_errors(self, success_types=['CONFIGURABLE', 'OAUTH']):
        return self.addon_type not in success_types


class NodeOAuthAddonTestSuiteMixin(NodeAddonTestSuiteMixin):
    addon_type = 'OAUTH'

    @abc.abstractproperty
    def AccountFactory(self):
        pass

    @abc.abstractproperty
    def NodeSettingsFactory(self):
        pass

    def _apply_auth_configuration(self, *args, **kwargs):
        settings = self._settings_kwargs(self.node, self.user_settings)
        for key in settings:
            setattr(self.node_settings, key, settings[key])
        self.node_settings.external_account = self.account
        self.node_settings.save()


class NodeConfigurableAddonTestSuiteMixin(NodeOAuthAddonTestSuiteMixin):
    addon_type = 'CONFIGURABLE'

    def _mock_folder_info(self):
        return '0987654321'

    def test_folder_list_raises_error_if_not_GET(self):
        pass

    def test_folder_list_GET_raises_error_noncontrib_not_public(self):
        pass

    def test_folder_list_GET_raises_error_writecontrib_not_authorizer(self):
        pass

    def test_folder_list_GET_raises_error_admin_not_authorizer(self):
        pass

class NodeOAuthCitationAddonTestSuiteMixin(NodeOAuthAddonTestSuiteMixin):
    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'list_id': 'fake_folder_id',
            'owner': self.node
        }


class NodeManageableAddonTestSuiteMixin(NodeAddonTestSuiteMixin):
    addon_type = 'MANAGEABLE'


class NodeUnmanageableAddonTestSuiteMixin(NodeAddonTestSuiteMixin):
    addon_type = 'UNMANAGEABLE'


class TestNodeInvalidAddon(NodeAddonTestSuiteMixin, ApiAddonTestCase):
    addon_type = 'INVALID'
    short_name = 'fake'


# UNMANAGEABLE


class TestNodeForwardAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'forward'


class TestNodeOsfStorageAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'osfstorage'


class TestNodeTwoFactorAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'twofactor'


class TestNodeWikiAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'wiki'


class TestNodeFigshareAddon(NodeUnmanageableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'figshare'


# OAUTH


class TestNodeDataverseAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'dataverse'
    AccountFactory = DataverseAccountFactory
    NodeSettingsFactory = DataverseNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            '_dataset_id': '1234567890',
            'owner': self.node
        }


class TestNodeGitHubAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'github'
    AccountFactory = GitHubAccountFactory
    NodeSettingsFactory = GitHubNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'repo': 'mock',
            'user': 'abc',
            'owner': self.node
        }


class TestNodeMendeleyAddon(NodeOAuthCitationAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'mendeley'
    AccountFactory = MendeleyAccountFactory
    NodeSettingsFactory = MendeleyNodeSettingsFactory


class TestNodeZoteroAddon(NodeOAuthCitationAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'zotero'
    AccountFactory = ZoteroAccountFactory
    NodeSettingsFactory = ZoteroNodeSettingsFactory


class TestNodeBoxAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'box'
    AccountFactory = BoxAccountFactory
    NodeSettingsFactory = BoxNodeSettingsFactory


class TestNodeDropboxAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'dropbox'
    AccountFactory = DropboxAccountFactory
    NodeSettingsFactory = DropboxNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder': '1234567890',
            'owner': self.node
        }


class TestNodeS3Addon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 's3'
    AccountFactory = S3AccountFactory
    NodeSettingsFactory = S3NodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'owner': self.node
        }


# CONFIGURABLE


class TestNodeGoogleDriveAddon(NodeConfigurableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'googledrive'
    AccountFactory = GoogleDriveAccountFactory
    NodeSettingsFactory = GoogleDriveNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'folder_id': '1234567890',
            'folder_path': '/1234567890'
        }

    def _mock_folder_info(self):
        return {
            'id': '0987654321',
            'path': '/'
        }

