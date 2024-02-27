import pytest
import unittest
from unittest import mock
from framework.auth import Auth

from addons.base.tests.utils import MockFolder, MockLibrary

from pyzotero.zotero_errors import UserNotAuthorised
from osf_tests.factories import ProjectFactory

from addons.base.tests.models import (
    CitationAddonProviderTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin,
    OAuthCitationsNodeSettingsTestSuiteMixin,
)
from addons.zotero.models import (
    Zotero, NodeSettings,
)
from addons.zotero.tests.factories import (
    ZoteroAccountFactory,
    ZoteroNodeSettingsFactory,
    ZoteroUserSettingsFactory,
)

from addons.zotero.provider import ZoteroCitationsProvider

pytestmark = pytest.mark.django_db


class ZoteroProviderTestCase(CitationAddonProviderTestSuiteMixin, unittest.TestCase):

    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory
    ProviderClass = ZoteroCitationsProvider
    OAuthProviderClass = Zotero
    ApiExceptionClass = UserNotAuthorised

    def test_handle_callback(self):
        response = {
            'userID': 'Fake User ID',
            'username': 'Fake User Name',
        }

        res = self.provider.handle_callback(response)

        assert (res.get('display_name') == 'Fake User Name')
        assert (res.get('provider_id') == 'Fake User ID')


class ZoteroNodeSettingsTestCase(OAuthCitationsNodeSettingsTestSuiteMixin, unittest.TestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ProviderClass = ZoteroCitationsProvider
    OAuthProviderClass = Zotero
    ExternalAccountFactory = ZoteroAccountFactory

    NodeSettingsFactory = ZoteroNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = ZoteroUserSettingsFactory

    def setUp(self):
        super().setUp()
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id', 'library': 'fake_library_id'}
        )
        self.user_settings.save()

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'list_id': 'fake_folder_id',
            'library_id': 'fake_library_id',
            'owner': self.node
        }

    def test_fields(self):
        node_settings = self.NodeSettingsClass(owner=ProjectFactory(), user_settings=self.user_settings)
        node_settings.save()
        assert node_settings.user_settings
        assert node_settings.user_settings.owner == self.user
        assert hasattr(node_settings, 'folder_id')
        assert hasattr(node_settings, 'library_id')
        assert hasattr(node_settings, 'user_settings')

    def test_library_defaults_to_none(self):
        node_settings = self.NodeSettingsClass(user_settings=self.user_settings)
        node_settings.save()
        assert node_settings.library_id is None

    def test_clear_settings(self):
        node_settings = self.NodeSettingsFactory()
        node_settings.external_account = self.ExternalAccountFactory()
        node_settings.user_settings = self.UserSettingsFactory()
        node_settings.save()

        node_settings.clear_settings()
        assert node_settings.folder_id is None
        assert node_settings.library_id is None

    def test_delete(self):
        assert self.node_settings.user_settings
        assert self.node_settings.folder_id
        old_logs = list(self.node.logs.all())
        self.node_settings.delete()
        self.node_settings.save()
        assert self.node_settings.user_settings is None
        assert self.node_settings.folder_id is None
        assert self.node_settings.library_id is None
        assert self.node_settings.deleted
        assert list(self.node.logs.all()) == list(old_logs)

    def test_deauthorize(self):
        assert self.node_settings.user_settings
        assert self.node_settings.folder_id
        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()
        assert self.node_settings.user_settings is None
        assert self.node_settings.folder_id is None
        assert self.node_settings.library_id is None

        last_log = self.node.logs.first()
        assert last_log.action == f'{self.short_name}_node_deauthorized'
        params = last_log.params
        assert 'node' in params
        assert 'project' in params

    def test_fetch_library_name_personal(self):
        self.node_settings.library_id = 'personal'

        assert self.node_settings.fetch_library_name == 'My library'

    @mock.patch('addons.zotero.models.Zotero._fetch_libraries')
    def test_get_folders_top_level(self, mock_libraries):
        """
        Top level folders in Zotero are group libraries + personal libraries
        """
        mock_libraries.return_value = [MockLibrary(), MockLibrary()]
        # No path is specified, so top level libraries are fetched
        libraries = self.node_settings.get_folders()

        assert len(libraries) == 2
        assert libraries[0]['kind'] == 'library'
        assert libraries[1]['kind'] == 'library'

    @mock.patch('addons.zotero.models.Zotero._get_folders')
    def test_get_folders_second_level(self, mock_folders):
        """
        Second level folders are folders within group/personal libraries
        """
        mock_folders.return_value = [MockFolder(), MockFolder()]
        # Path - personal, is specified, so folders are fetched from personal library.
        folders = self.node_settings.get_folders('personal')

        assert len(folders) == 3
        assert folders[0]['kind'] == 'folder'
        assert folders[0]['name'] == 'All Documents'
        assert folders[1]['kind'] == 'folder'
        assert folders[2]['kind'] == 'folder'

    def test_selected_library_name_empty(self):
        self.node_settings.library_id = None

        assert self.node_settings.fetch_library_name == ''

    def test_selected_library_name(self):
        # Mock the return from api call to get the library's name
        mock_library = MockLibrary()
        name = None

        with mock.patch.object(self.OAuthProviderClass, '_library_metadata', return_value=mock_library):
            name = self.node_settings.fetch_library_name

        assert name == 'Fake Library'

    def test_set_library(self):
        folder_id = 'fake-folder-id'
        folder_name = 'fake-folder-name'
        library_id = 'fake-library-id'
        library_name = 'fake-library-name'

        self.node_settings.clear_settings()
        self.node_settings.save()
        self.node_settings.list_id = folder_id
        self.node_settings.save()
        assert self.node_settings.list_id == folder_id

        provider = self.ProviderClass()

        provider.set_config(
            self.node_settings,
            self.user,
            folder_id,
            folder_name,
            Auth(user=self.user),
            library_id,
            library_name,
        )

        # instance was updated
        assert self.node_settings.library_id == 'fake-library-id'
        # If library_id is being set, the folder_id is cleared.
        assert self.node_settings.list_id is None

        # user_settings was updated
        # TODO: the call to grant_oauth_access should be mocked
        assert self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'library': 'fake-library-id'}
            )

        log = self.node.logs.latest()
        assert log.action == f'{self.short_name}_library_selected'
        assert log.params['library_id'] == library_id
        assert log.params['library_name'] == library_name


class ZoteroUserSettingsTestCase(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory

    def test_grant_oauth_access_metadata_with_library(self):
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'library': 'fake_library_id'}
        )
        self.user_settings.save()

        assert self.user_settings.oauth_grants == {
            self.node._id: {
                self.external_account._id: {'library': 'fake_library_id'}
            },
        }

    def test_verify_oauth_access_metadata_with_library(self):
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'library': 'fake_library_id'}
        )
        self.user_settings.save()

        assert self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'library': 'fake_library_id'}
            )

        assert not self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'library': 'another_library_id'}
            )
