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
        self.assertTrue(node_settings.user_settings)
        self.assertEqual(node_settings.user_settings.owner, self.user)
        self.assertTrue(hasattr(node_settings, 'folder_id'))
        self.assertTrue(hasattr(node_settings, 'library_id'))
        self.assertTrue(hasattr(node_settings, 'user_settings'))

    def test_library_defaults_to_none(self):
        node_settings = self.NodeSettingsClass(user_settings=self.user_settings)
        node_settings.save()
        self.assertIsNone(node_settings.library_id)

    def test_clear_settings(self):
        node_settings = self.NodeSettingsFactory()
        node_settings.external_account = self.ExternalAccountFactory()
        node_settings.user_settings = self.UserSettingsFactory()
        node_settings.save()

        node_settings.clear_settings()
        self.assertIsNone(node_settings.folder_id)
        self.assertIsNone(node_settings.library_id)

    def test_delete(self):
        self.assertTrue(self.node_settings.user_settings)
        self.assertTrue(self.node_settings.folder_id)
        old_logs = list(self.node.logs.all())
        self.node_settings.delete()
        self.node_settings.save()
        self.assertIs(self.node_settings.user_settings, None)
        self.assertIs(self.node_settings.folder_id, None)
        self.assertIs(self.node_settings.library_id, None)
        self.assertTrue(self.node_settings.deleted)
        self.assertEqual(list(self.node.logs.all()), list(old_logs))

    def test_deauthorize(self):
        self.assertTrue(self.node_settings.user_settings)
        self.assertTrue(self.node_settings.folder_id)
        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()
        self.assertIs(self.node_settings.user_settings, None)
        self.assertIs(self.node_settings.folder_id, None)
        self.assertIs(self.node_settings.library_id, None)

        last_log = self.node.logs.first()
        self.assertEqual(last_log.action, f'{self.short_name}_node_deauthorized')
        params = last_log.params
        self.assertIn('node', params)
        self.assertIn('project', params)

    def test_fetch_library_name_personal(self):
        self.node_settings.library_id = 'personal'

        self.assertEqual(
            self.node_settings.fetch_library_name,
            'My library'
        )

    @mock.patch('addons.zotero.models.Zotero._fetch_libraries')
    def test_get_folders_top_level(self, mock_libraries):
        """
        Top level folders in Zotero are group libraries + personal libraries
        """
        mock_libraries.return_value = [MockLibrary(), MockLibrary()]
        # No path is specified, so top level libraries are fetched
        libraries = self.node_settings.get_folders()

        self.assertEqual(len(libraries), 2)
        self.assertEqual(libraries[0]['kind'], 'library')
        self.assertEqual(libraries[1]['kind'], 'library')

    @mock.patch('addons.zotero.models.Zotero._get_folders')
    def test_get_folders_second_level(self, mock_folders):
        """
        Second level folders are folders within group/personal libraries
        """
        mock_folders.return_value = [MockFolder(), MockFolder()]
        # Path - personal, is specified, so folders are fetched from personal library.
        folders = self.node_settings.get_folders('personal')

        self.assertEqual(len(folders), 3)
        self.assertEqual(folders[0]['kind'], 'folder')
        self.assertEqual(folders[0]['name'], 'All Documents')
        self.assertEqual(folders[1]['kind'], 'folder')
        self.assertEqual(folders[2]['kind'], 'folder')

    def test_selected_library_name_empty(self):
        self.node_settings.library_id = None

        self.assertEqual(
            self.node_settings.fetch_library_name,
            ''
        )

    def test_selected_library_name(self):
        # Mock the return from api call to get the library's name
        mock_library = MockLibrary()
        name = None

        with mock.patch.object(self.OAuthProviderClass, '_library_metadata', return_value=mock_library):
            name = self.node_settings.fetch_library_name

        self.assertEqual(
            name,
            'Fake Library'
        )

    def test_set_library(self):
        folder_id = 'fake-folder-id'
        folder_name = 'fake-folder-name'
        library_id = 'fake-library-id'
        library_name = 'fake-library-name'

        self.node_settings.clear_settings()
        self.node_settings.save()
        self.node_settings.list_id = folder_id
        self.node_settings.save()
        self.assertEqual(self.node_settings.list_id, folder_id)

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
        self.assertEqual(
            self.node_settings.library_id,
            'fake-library-id',
        )
        # If library_id is being set, the folder_id is cleared.
        self.assertEqual(
            self.node_settings.list_id,
            None,
        )

        # user_settings was updated
        # TODO: the call to grant_oauth_access should be mocked
        self.assertTrue(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'library': 'fake-library-id'}
            )
        )

        log = self.node.logs.latest()
        self.assertEqual(log.action, f'{self.short_name}_library_selected')
        self.assertEqual(log.params['library_id'], library_id)
        self.assertEqual(log.params['library_name'], library_name)



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

        self.assertTrue(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'library': 'fake_library_id'}
            )
        )

        self.assertFalse(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'library': 'another_library_id'}
            )
        )
