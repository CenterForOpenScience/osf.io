# -*- coding: utf-8 -*-
import abc
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiAddonTestCase

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

    def test_settings_list_GET_returns_node_settings_if_enabled(self):
        pass

    def test_settings_list_GET_returns_disabled_if_disabled(self):
        pass

    def test_settings_list_raises_error_if_not_GET(self):
        pass

    def test_settings_list_raises_error_if_noncontrib_not_public(self):
        pass

    def test_settings_list_noncontrib_public_can_view(self):
        pass


class NodeAddonDetailMixin(object):
    def set_setting_detail_url(self):
        self.setting_detail_url = '/{}nodes/{}/addons/{}/'.format(
            API_BASE, self.node._id, self.short_name
        )

    def test_settings_detail_GET_returns_node_settings_if_enabled(self):
        pass

    def test_settings_detail_GET_returns_disabled_if_disabled(self):
        pass

    def test_settings_detail_PUT_all_sets(self):
        pass

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


class NodeAddonTestSuiteMixin(NodeAddonListMixin, NodeAddonDetailMixin):
    def set_urls(self):
        self.set_setting_list_url()
        self.set_setting_detail_url()


class NodeOAuthAddonTestSuiteMixin(NodeAddonTestSuiteMixin)
    addon_type = 'OAUTH'

    @abc.abstractproperty
    def AccountFactory(self):
        pass

    @abc.abstractproperty
    def NodeSettingsFactory(self):
        pass

    def _apply_auth_configuration(self, *args, **kwargs):
        self.node_settings = self.NodeSettingsFactory(
            **self._settings_kwargs(self.node, self.user_settings)
        )
        self.node_settings.external_account = self.account
        self.node_settings.save()


class NodeConfigurableAddonTestSuiteMixin(NodeOAuthAddonTestSuiteMixin):
    addon_type = 'CONFIGURABLE'

    def _folder_info(self):
        return '0987654321'


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


# MANAGEABLE


class TestNodeFigshareAddon(NodeManageableAddonTestSuiteMixin, ApiAddonTestCase):
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


# CONFIGURABLE


class TestNodeBoxAddon(NodeConfigurableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'box'
    AccountFactory = BoxAccountFactory
    NodeSettingsFactory = BoxNodeSettingsFactory


class TestNodeDropboxAddon(NodeConfigurableAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'dropbox'
    AccountFactory = DropboxAccountFactory
    NodeSettingsFactory = DropboxNodeSettingsFactory

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder': '1234567890',
            'owner': self.node
        }


class TestNodeGoogleDriveAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'googledrive'
    AccountFactory = GoogleDriveAccountFactory
    NodeSettingsFactory = GoogleDriveNodeSettingsFactory

    def _folder_info(self):
        return {
            'id': '0987654321',
            'path': '/'
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
