import abc

from unittest import mock
import pytest

from framework.auth import Auth
from osf_tests.factories import ProjectFactory, AuthUserFactory
from tests.utils import mock_auth
from website.util import web_url_for


class AddonSerializerTestSuiteMixin:

    __metaclass__ = abc.ABCMeta

    @property
    @abc.abstractmethod
    def Serializer(self):
        pass

    @property
    @abc.abstractmethod
    def ExternalAccountFactory(self):
        pass

    @abc.abstractmethod
    def set_user_settings(self, user):
        pass

    @abc.abstractmethod
    def set_node_settings(self, user_settings):
        pass

    @property
    @abc.abstractmethod
    def required_settings(self):
        pass

    @property
    @abc.abstractmethod
    def required_settings_authorized(self):
        pass

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.set_user_settings(self.user)
        assert getattr(self, 'user_settings') is not None, "'set_user_settings' should set the 'user_settings' attribute of the instance to an instance of \
             the appropriate user settings model."

        self.set_node_settings(self.user_settings)
        assert getattr(self, 'node_settings') is not None, "'set_node_settings' should set the 'user_settings' attribute of the instance to an instance of \
            the appropriate node settings model."

        self.ser = self.Serializer(
            user_settings=self.user_settings,
            node_settings=self.node_settings
        )

    def test_serialized_node_settings_unauthorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=False):
            serialized = self.ser.serialized_node_settings
        for setting in self.required_settings:
            assert setting in serialized

    def test_serialized_node_settings_authorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            serialized = self.ser.serialized_node_settings
        for setting in self.required_settings:
            assert setting in serialized
        for setting in self.required_settings_authorized:
            assert setting in serialized


class OAuthAddonSerializerTestSuiteMixin(AddonSerializerTestSuiteMixin):

    def set_user_settings(self, user):
        self.user_settings = user.get_or_add_addon(self.addon_short_name)
        self.external_account = self.ExternalAccountFactory()
        self.user.external_accounts.add(self.external_account)
        self.user.save()

    def set_node_settings(self, user_settings):
        self.node_settings = self.node.get_or_add_addon(self.addon_short_name, auth=Auth(user_settings.owner))
        self.node_settings.set_auth(self.user_settings.external_accounts[0], self.user)

    def test_credentials_owner(self):
        owner = self.ser.credentials_owner
        assert owner._id == self.user_settings.owner._id

    def test_user_is_owner_no_user_settings(self):
        ser = self.Serializer(node_settings=self.node_settings)
        assert not ser.user_is_owner

    def test_user_is_owner_no_node_settings(self):
        ser = self.Serializer(user_settings=self.user_settings)
        assert not ser.user_is_owner

    def test_user_is_owner_node_not_authorized_user_has_no_accounts(self):
        self.user.external_accounts.clear()
        assert not self.user_settings.external_accounts.count()
        assert not self.ser.user_is_owner

    def test_user_is_owner_node_not_authorized_user_has_accounts(self):
        assert self.user_settings.external_accounts.count()
        assert self.ser.user_is_owner

    def test_user_is_owner_node_authorized_user_is_not_owner(self):
        self.node_settings.external_account = self.ExternalAccountFactory()
        with mock.patch('addons.base.models.BaseOAuthUserSettings.verify_oauth_access',
                return_value=True):
            self.user.external_accounts.clear()
            assert not self.ser.user_is_owner

    def test_user_is_owner_node_authorized_user_is_owner(self):
        assert self.ser.user_is_owner

    def test_serialized_urls_checks_required(self):
        with mock.patch.object(self.ser, 'REQUIRED_URLS', ('foobar', )):
            with pytest.raises(AssertionError):
                self.ser.serialized_urls

    def test_serialized_acccounts(self):
        ea = self.ExternalAccountFactory()
        self.user.external_accounts.add(ea)

        with mock.patch.object(type(self.ser), 'serialize_account') as mock_serialize_account:
            mock_serialize_account.return_value = {}
            serialized = self.ser.serialized_accounts
        assert len(serialized) == self.user.external_accounts.count()
        assert mock_serialize_account.call_count == len(serialized)

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
        assert self.ser.serialize_account(ea) == expected

    def test_serialized_user_settings(self):
        with mock.patch.object(self.Serializer, 'serialized_accounts', return_value=[]):
            serialized = self.ser.serialized_user_settings
        assert 'accounts' in serialized

    def test_serialize_granted_node(self):
        with mock_auth(self.user):
            serialized = self.ser.serialize_granted_node(self.node, auth=Auth(self.user))
        for key in ('id', 'title', 'urls'):
            assert key in serialized
        assert self.node._id == serialized['id']
        assert self.node.title == serialized['title']
        assert 'view' in serialized['urls']
        assert serialized['urls']['view'] == self.node.url


class StorageAddonSerializerTestSuiteMixin(OAuthAddonSerializerTestSuiteMixin):

    required_settings = ('userIsOwner', 'nodeHasAuth', 'urls', 'userHasAuth')
    required_settings_authorized = ('ownerName', )

    @property
    @abc.abstractmethod
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
            assert key in serialized

    def test_serialize_settings_authorized(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        for key in self.required_settings:
            assert key in serialized
        assert 'owner' in serialized['urls']
        assert serialized['urls']['owner'] == web_url_for(
            'profile_view_id',
            uid=self.user_settings.owner._id
        )
        assert 'ownerName' in serialized
        assert serialized['ownerName'] == self.user_settings.owner.fullname
        assert 'folder' in serialized

    def test_serialize_settings_authorized_no_folder(self):
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        assert 'folder' in serialized
        assert serialized['folder'] == {'name': None, 'path': None}

    def test_serialize_settings_authorized_folder_is_set(self):
        self.set_provider_id('foo')
        with mock.patch.object(type(self.node_settings), 'has_auth', return_value=True):
            with mock.patch.object(self.ser, 'serialized_folder') as mock_serialized_folder:
                mock_serialized_folder.return_value = {}
                serialized = self.ser.serialize_settings(self.node_settings, self.user, self.client)
        assert 'folder' in serialized
        assert mock_serialized_folder.called


class CitationAddonSerializerTestSuiteMixin(OAuthAddonSerializerTestSuiteMixin):
    required_settings = ('userIsOwner', 'nodeHasAuth', 'urls', 'userHasAuth')
    required_settings_authorized = ('ownerName', )

    @property
    @abc.abstractmethod
    def folder(self):
        pass

    def test_serialize_folder(self):
        serialized_folder = self.ser.serialize_folder(self.folder)
        assert serialized_folder['id'] == self.folder['id']
        assert serialized_folder['name'] == self.folder.name
        assert serialized_folder['kind'] == 'folder'

    def test_serialize_citation(self):
        serialized_citation = self.ser.serialize_citation(self.folder)
        assert serialized_citation['csl'] == self.folder
        assert serialized_citation['id'] == self.folder['id']
        assert serialized_citation['kind'] == 'file'
