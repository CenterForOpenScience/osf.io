# -*- coding: utf-8 -*-
import abc

import mock
from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth

from website.util import web_url_for

from tests.factories import AuthUserFactory, ProjectFactory
from tests.utils import mock_auth

class AddonSerializerTestSuiteMixin(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def Serializer(self):
        pass

    @abc.abstractproperty
    def ExternalAccountFactory(self):
        pass

    @abc.abstractmethod
    def set_user_settings(self, user):
        pass

    @abc.abstractmethod
    def set_node_settings(self, user_settings):
        pass

    @abc.abstractproperty
    def required_settings(self):
        pass

    @abc.abstractproperty
    def required_settings_authorized(self):
        pass

    def setUp(self):
        super(AddonSerializerTestSuiteMixin, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.set_user_settings(self.user)
        assert_is_not_none(
            getattr(self, 'user_settings'),
            "'set_user_settings' should set the 'user_settings' attribute of the instance to an instance of the appropriate user settings model."
        )
        self.set_node_settings(self.user_settings)
        assert_is_not_none(
            getattr(self, 'node_settings'),
            "'set_node_settings' should set the 'user_settings' attribute of the instance to an instance of the appropriate node settings model."
        )

        self.ser = self.Serializer(
            user_settings=self.user_settings,
            node_settings=self.node_settings
        )

    def test_serialized_node_settings_unauthorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=False):
            serialized = self.ser.serialized_node_settings
        for setting in self.required_settings:
            assert_in(setting, serialized)

    def test_serialized_node_settings_authorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            serialized = self.ser.serialized_node_settings
        for setting in self.required_settings:
            assert_in(setting, serialized)
        for setting in self.required_settings_authorized:
            assert_in(setting, serialized)


class OAuthAddonSerializerTestSuiteMixin(AddonSerializerTestSuiteMixin):

    def set_user_settings(self, user):
        self.user_settings = user.get_or_add_addon(self.addon_short_name, auth=Auth(user))
        self.external_account = self.ExternalAccountFactory()
        self.user.external_accounts.append(self.external_account)
        self.user.save()

    def set_node_settings(self, user_settings):
        self.node_settings = self.node.get_or_add_addon(self.addon_short_name, auth=Auth(user_settings.owner))
        self.node_settings.set_auth(self.user_settings.external_accounts[0], self.user)

    def test_credentials_owner(self):
        owner = self.ser.credentials_owner
        assert_equal(owner._id, self.user_settings.owner._id)

    def test_user_is_owner_no_user_settings(self):
        ser = self.Serializer(node_settings=self.node_settings)
        assert_false(ser.user_is_owner)

    def test_user_is_owner_no_node_settings(self):
        ser = self.Serializer(user_settings=self.user_settings)
        assert_false(ser.user_is_owner)

    def test_user_is_owner_node_not_authorized_user_has_no_accounts(self):
        self.user.external_accounts = []
        assert_false(len(self.user_settings.external_accounts))
        assert_false(self.ser.user_is_owner)

    def test_user_is_owner_node_not_authorized_user_has_accounts(self):
        assert_true(len(self.user_settings.external_accounts))
        assert_true(self.ser.user_is_owner)

    def test_user_is_owner_node_authorized_user_is_not_owner(self):
        self.node_settings.external_account = self.ExternalAccountFactory()
        with mock.patch('website.addons.base.AddonOAuthUserSettingsBase.verify_oauth_access', return_value=True):
            self.user.external_accounts = []
            assert_false(self.ser.user_is_owner)

    def test_user_is_owner_node_authorized_user_is_owner(self):
        assert_true(self.ser.user_is_owner)

    def test_serialized_urls_checks_required(self):
        with mock.patch.object(self.ser, 'REQUIRED_URLS', ('foobar', )):
            with assert_raises(AssertionError):
                self.ser.serialized_urls

    def test_serialized_acccounts(self):
        ea = self.ExternalAccountFactory()
        self.user.external_accounts.append(ea)

        with mock.patch.object(type(self.ser), 'serialize_account') as mock_serialize_account:
            mock_serialize_account.return_value = {}
            serialized = self.ser.serialized_accounts
        assert_equal(len(serialized), len(self.user.external_accounts))
        assert_equal(mock_serialize_account.call_count, len(serialized))

    def test_serialize_acccount(self):
        ea = self.ExternalAccountFactory()
        expected = {
            'id': ea._id,
            'provider_id': ea.provider_id,
            'provider_name': ea.provider_name,
            'provider_short_name': ea.provider,
            'display_name': ea.display_name,
            'profile_url': ea.profile_url,
            'nodes': [],
        }
        assert_equal(self.ser.serialize_account(ea), expected)

    def test_serialized_user_settings(self):
        with mock.patch.object(self.Serializer, 'serialized_accounts', return_value=[]):
            serialized = self.ser.serialized_user_settings
        assert_in('accounts', serialized)

    def test_serialize_granted_node(self):
        with mock_auth(self.user):
            serialized = self.ser.serialize_granted_node(self.node, auth=Auth(self.user))
        for key in ('id', 'title', 'urls'):
            assert_in(key, serialized)
        assert_equal(self.node._id, serialized['id'])
        assert_equal(self.node.title, serialized['title'])
        assert_in('view', serialized['urls'])
        assert_equal(serialized['urls']['view'], self.node.url)


class StorageAddonSerializerTestSuiteMixin(OAuthAddonSerializerTestSuiteMixin):

    required_settings = ('userIsOwner', 'nodeHasAuth', 'urls', 'userHasAuth')
    required_settings_authorized = ('ownerName', )

    @abc.abstractproperty
    def client(self):
        """Provide a mocked version of this provider's client (i.e. the client should not make
        acutal API calls).
        """
        pass

    @abc.abstractmethod
    def set_provider_id(self):
        pass

    def test_serialize_settings_unauthorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=False):
            serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        for key in self.required_settings:
            assert_in(key, serialized)

    def test_serialize_settings_authorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        for key in self.required_settings:
            assert_in(key, serialized)
        assert_in('owner', serialized['urls'])
        assert_equal(serialized['urls']['owner'], web_url_for(
            'profile_view_id',
            uid=self.user_settings.owner._id
        ))
        assert_in('ownerName', serialized)
        assert_equal(serialized['ownerName'], self.user_settings.owner.fullname)
        assert_in('folder', serialized)

    def test_serialize_settings_authorized_no_folder(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        assert_in('folder', serialized)
        assert_equal(serialized['folder'], {'name': None, 'path': None})

    def test_serialize_settings_authorized_folder_is_set(self):
        self.set_provider_id('foo')
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            with mock.patch.object(self.ser, 'serialized_folder') as mock_serialized_folder:
                mock_serialized_folder.return_value = {}
                serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        assert_in('folder', serialized)
        assert_true(mock_serialized_folder.called)
