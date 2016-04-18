# -*- coding: utf-8 -*-
import abc
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiAddonTestCase

from website.addons.box.tests.factories import BoxAccountFactory, BoxNodeSettingsFactory

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

    def test_settings_detail_PUT_toggles_enabled_disabled(self):
        pass

    def test_settings_detail_PATCH_toggles_enabled_disabled(self):
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

class NodeAddonAccountListMixin(object):
    def set_account_list_url(self):
        self.account_list_url = '/{}nodes/{}/addons/{}/accounts/?page[size]=100'.format(
            API_BASE, self.node._id, self.short_name
        )

    def test_account_list_GET_returns_account_if_enabled(self):
        pass

    def test_account_list_returns_nothing_if_disabled(self):
        pass

    def test_account_list_POST_account_enables_addon(self):
        pass

    def test_account_list_POST_by_nonadmin_raises_error(self):
        pass

    def test_account_list_raises_error_if_DELETE_PUT_or_PATCH(self):
        pass

    def test_account_list_raises_error_if_noncontrib_not_public(self):
        pass

    def test_account_list_noncontrib_public_can_view(self):
        pass

    def test_account_list_noncontrib_public_cannot_edit(self):
        pass


class NodeAddonAccountDetailMixin(object):
    def set_account_detail_url(self):
        self.account_detail_url = '/{}nodes/{}/addons/{}/accounts/{}'.format(
            API_BASE, self.node._id, self.short_name,
            self.account._id if self.account else ''
        )

    def test_account_detail_GET_returns_account_if_enabled(self):
        pass

    def test_account_detail_raises_error_if_disabled(self):
        pass

    def test_account_detail_DELETE_account_disables_addon(self):
        pass

    def test_account_detail_raises_error_if_POST_PUT_or_PATCH(self):
        pass

    def test_account_detail_DELETE_raises_error_if_contrib_not_admin(self):
        pass

    def test_account_detail_raises_error_if_noncontrib_not_public(self):
        pass

    def test_account_detail_noncontrib_public_can_view(self):
        pass

    def test_account_detail_noncontrib_public_cannot_edit(self):
        pass


class NodeAddonTestSuiteMixin(NodeAddonListMixin, NodeAddonDetailMixin, NodeAddonAccountListMixin, NodeAddonAccountDetailMixin):
    def set_urls(self):
        self.set_setting_list_url()
        self.set_setting_detail_url()
        self.set_account_list_url()
        self.set_account_detail_url()

class NodeOAuthAddonTestSuiteMixin(NodeAddonTestSuiteMixin):
    addon_type = 'OAUTH'

    @abc.abstractproperty
    def NodeSettingsFactory(self):
        pass

    def _apply_auth_configuration(self, *args, **kwargs):
        self.node_settings = self.NodeSettingsFactory(
            **self._settings_kwargs(self.node, self.user_settings)
        )
        self.node_settings.external_account = self.account
        self.node_settings.save()

class TestNodeBoxAddon(NodeOAuthAddonTestSuiteMixin, ApiAddonTestCase):
    short_name = 'box'
    AccountFactory = BoxAccountFactory
    NodeSettingsFactory = BoxNodeSettingsFactory

    def setUp(self):
        super(TestNodeBoxAddon, self).setUp()
        self.set_urls()
