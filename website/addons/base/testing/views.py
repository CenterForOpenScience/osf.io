# -*- coding: utf-8 -*-
import httplib as http
import urlparse

import mock
from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth

from website.addons.base.testing.base import OAuthAddonTestCaseMixin
from website.util import api_url_for, web_url_for, permissions

from tests.factories import AuthUserFactory, ProjectFactory


class OAuthAddonAuthViewsTestCaseMixin(OAuthAddonTestCaseMixin):

    @property
    def Provider(self):
        raise NotImplementedError()

    def test_oauth_start(self):
        url = api_url_for(
            'oauth_connect',
            service_name=self.ADDON_SHORT_NAME
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.FOUND)
        redirect_url = urlparse.urlparse(res.location)
        redirect_params = urlparse.parse_qs(redirect_url.query)
        provider_url = urlparse.urlparse(self.Provider().auth_url)
        provider_params = urlparse.parse_qs(provider_url.query)
        for param, value in redirect_params.items():
            if param == 'state':  # state may change between calls
                continue
            assert_equal(value, provider_params[param])

    def test_oauth_finish(self):
        url = web_url_for(
            'oauth_callback',
            service_name=self.ADDON_SHORT_NAME
        )
        with mock.patch.object(self.Provider, 'auth_callback') as mock_callback:
            mock_callback.return_value = True
            res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        name, args, kwargs = mock_callback.mock_calls[0]
        assert_equal(kwargs['user']._id, self.user._id)

    def test_delete_external_account(self):
        url = api_url_for(
            'oauth_disconnect',
            external_account_id=self.external_account._id
        )
        res = self.app.delete(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        self.user.reload()
        for account in self.user.external_accounts:
            assert_not_equal(account._id, self.external_account._id)
        assert_false(self.user.external_accounts)

    def test_delete_external_account_not_owner(self):
        other_user = AuthUserFactory()
        url = api_url_for(
            'oauth_disconnect',
            external_account_id=self.external_account._id
        )
        res = self.app.delete(url, auth=other_user.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

class OAuthAddonConfigViewsTestCaseMixin(OAuthAddonTestCaseMixin):

    @property
    def folder(self):
        raise NotImplementedError("This test suite must expose a 'folder' property.")

    @property
    def Serializer(self):
        raise NotImplementedError()

    @property
    def client(self):
        raise NotImplementedError()

    def test_import_auth(self):
        ea = self.ExternalAccountFactory()
        self.user.external_accounts.append(ea)
        self.user.save()

        node = ProjectFactory(creator=self.user)
        node_settings = node.get_or_add_addon(self.ADDON_SHORT_NAME, auth=Auth(self.user))
        node.save()
        url = node.api_url_for('{0}_import_auth'.format(self.ADDON_SHORT_NAME))
        res = self.app.put_json(url, {
            'external_account_id': ea._id
        }, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        assert_in('result', res.json)
        node_settings.reload()
        assert_equal(node_settings.external_account._id, ea._id)

        node.reload()
        last_log = node.logs[-1]
        assert_equal(last_log.action, '{0}_node_authorized'.format(self.ADDON_SHORT_NAME))

    def test_import_auth_invalid_account(self):
        ea = self.ExternalAccountFactory()

        node = ProjectFactory(creator=self.user)
        node.add_addon(self.ADDON_SHORT_NAME, auth=self.auth)
        node.save()
        url = node.api_url_for('{0}_import_auth'.format(self.ADDON_SHORT_NAME))
        res = self.app.put_json(url, {
            'external_account_id': ea._id
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_import_auth_cant_write_node(self):
        ea = self.ExternalAccountFactory()
        user = AuthUserFactory()
        user.add_addon(self.ADDON_SHORT_NAME, auth=Auth(user))
        user.external_accounts.append(ea)
        user.save()

        node = ProjectFactory(creator=self.user)
        node.add_contributor(user, permissions=[permissions.READ], auth=self.auth, save=True)
        node.add_addon(self.ADDON_SHORT_NAME, auth=self.auth)
        node.save()
        url = node.api_url_for('{0}_import_auth'.format(self.ADDON_SHORT_NAME))
        res = self.app.put_json(url, {
            'external_account_id': ea._id
        }, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_set_config(self):
        url = self.project.api_url_for('{0}_set_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.put_json(url, {
            'selected': self.folder
        }, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        self.project.reload()
        assert_equal(
            self.project.logs[-1].action,
            '{0}_folder_selected'.format(self.ADDON_SHORT_NAME)
        )
        assert_equal(res.json['result']['folder']['path'], self.folder['path'])

    def test_get_config(self):
        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        with mock.patch.object(type(self.Serializer()), 'credentials_are_valid', return_value=True):
            res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        assert_in('result', res.json)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            self.user,
            self.client
        )
        assert_equal(serialized, res.json['result'])

    def test_get_config_unauthorized(self):
        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        user = AuthUserFactory()
        self.project.add_contributor(user, permissions=[permissions.READ], auth=self.auth, save=True)
        res = self.app.get(url, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_get_config_not_logged_in(self):
        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=None, expect_errors=True)
        assert_equal(res.status_code, http.FOUND)

    def test_account_list_single(self):
        url = api_url_for('{0}_account_list'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        assert_in('accounts', res.json)
        assert_equal(len(res.json['accounts']), 1)

    def test_account_list_multiple(self):
        ea = self.ExternalAccountFactory()
        self.user.external_accounts.append(ea)
        self.user.save()

        url = api_url_for('{0}_account_list'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        assert_in('accounts', res.json)
        assert_equal(len(res.json['accounts']), 2)

    def test_account_list_not_authorized(self):
        url = api_url_for('{0}_account_list'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=None, expect_errors=True)
        assert_equal(res.status_code, http.FOUND)

    def test_folder_list(self):
        # Note: if your addon's folder_list view makes API calls
        # then you will need to implement test_folder_list in your
        # subclass, mock any API calls, and call super.
        self.node_settings.set_auth(self.external_account, self.user)
        self.node_settings.save()
        url = self.project.api_url_for('{0}_folder_list'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        # TODO test result serialization?

    def test_deauthorize_node(self):
        url = self.project.api_url_for('{0}_deauthorize_node'.format(self.ADDON_SHORT_NAME))
        res = self.app.delete(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        self.node_settings.reload()
        assert_is_none(self.node_settings.external_account)
        assert_false(self.node_settings.has_auth)

        # A log event was saved
        self.project.reload()
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, '{0}_node_deauthorized'.format(self.ADDON_SHORT_NAME))
