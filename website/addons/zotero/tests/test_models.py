# -*- coding: utf-8 -*-

import mock
from nose.tools import *  # noqa

from framework.exceptions import PermissionsError

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.zotero.tests.factories import (
    ZoteroAccountFactory, ZoteroUserSettingsFactory,
    ExternalAccountFactory,
    ZoteroNodeSettingsFactory
)
from website.addons.zotero.provider import ZoteroCitationsProvider

import datetime

from website.addons.zotero import model


class ZoteroProviderTestCase(OsfTestCase):

    def setUp(self):
        super(ZoteroProviderTestCase, self).setUp()
        self.provider = model.Zotero()

    def test_handle_callback(self):
        mock_response = {
            'userID': 'Fake User ID',
            'username': 'Fake User Name',
        }

        res = self.provider.handle_callback(mock_response)

        assert_equal(res.get('display_name'), 'Fake User Name')
        assert_equal(res.get('provider_id'), 'Fake User ID')

    def test_citation_lists(self):
        mock_client = mock.Mock()
        mock_folders = [
            {
                'data': {
                    'name': 'Fake Folder',
                    'key': 'Fake Key',
                }
            }
        ]

        mock_client.collections.return_value = mock_folders
        self.provider._client = mock_client
        mock_account = mock.Mock()
        self.provider.account = mock_account

        res = self.provider.citation_lists(ZoteroCitationsProvider()._extract_folder)
        assert_equal(
            res[1]['name'],
            'Fake Folder'
        )
        assert_equal(
            res[1]['id'],
            'Fake Key'
        )

class ZoteroNodeSettingsTestCase(OsfTestCase):

    def setUp(self):
        super(ZoteroNodeSettingsTestCase, self).setUp()
        self.node = ProjectFactory()
        self.node_settings = model.ZoteroNodeSettings(owner=self.node)
        self.node_settings.save()
        self.user = self.node.creator
        self.user_settings = self.user.get_or_add_addon('zotero')

    def tearDown(self):
        super(ZoteroNodeSettingsTestCase, self).tearDown()
        self.user_settings.remove()
        self.node_settings.remove()
        self.node.remove()
        self.user.remove()

    @mock.patch('website.addons.zotero.model.Zotero')
    def test_api_not_cached(self, mock_zotero):
        # The first call to .api returns a new object
        api = self.node_settings.api
        mock_zotero.assert_called_once()
        assert_equal(api, mock_zotero())

    @mock.patch('website.addons.zotero.model.Zotero')
    def test_api_cached(self, mock_zotero):
        # Repeated calls to .api returns the same object
        self.node_settings._api = 'testapi'
        api = self.node_settings.api
        assert_false(mock_zotero.called)
        assert_equal(api, 'testapi')

    def test_set_auth(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        # this should be reset after the call
        self.node_settings.zotero_list_id = 'anything'

        self.node_settings.set_auth(
            external_account=external_account,
            user=self.user
        )

        # this instance is updated
        assert_equal(
            self.node_settings.external_account,
            external_account
        )
        assert_equal(
            self.node_settings.user_settings,
            self.user_settings
        )
        assert_is_none(
            self.node_settings.zotero_list_id
        )

        # user_settings was updated
        # TODO: The call to grant_oauth_access in set_auth should be mocked
        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=external_account,
            )
        )

    def test_set_auth_wrong_user(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        with assert_raises(PermissionsError):
            self.node_settings.set_auth(
                external_account=external_account,
                user=UserFactory()
            )

    def test_clear_auth(self):
        self.node_settings.external_account = ExternalAccountFactory()
        self.node_settings.zotero_list_id = 'something'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

        self.node_settings.clear_auth()

        assert_is_none(self.node_settings.external_account)
        assert_is_none(self.node_settings.zotero_list_id)
        assert_is_none(self.node_settings.user_settings)

    def test_set_target_folder(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        self.node_settings.set_auth(
            external_account=external_account,
            user=self.user
        )

        assert_is_none(self.node_settings.zotero_list_id)

        self.node_settings.set_target_folder('fake-folder-id')

        # instance was updated
        assert_equal(
            self.node_settings.zotero_list_id,
            'fake-folder-id',
        )

        # user_settings was updated
        # TODO: the call to grant_oauth_access should be mocked
        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=external_account,
                metadata={'folder': 'fake-folder-id'}
            )
        )

    def test_has_auth_false(self):
        external_account = ExternalAccountFactory()

        assert_false(self.node_settings.has_auth)

        # both external_account and user_settings must be set to have auth
        self.node_settings.external_account = external_account
        assert_false(self.node_settings.has_auth)

        self.node_settings.external_account = None
        self.node_settings.user_settings = self.user_settings
        assert_false(self.node_settings.has_auth)

        # set_auth must be called to have auth
        self.node_settings.external_account = external_account
        self.node_settings.user_settings = self.user_settings
        assert_false(self.node_settings.has_auth)

    def test_has_auth_true(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)

        self.node_settings.set_auth(external_account, self.user)

        # zotero_list_id should have no effect
        self.node_settings.zotero_list_id = None
        assert_true(self.node_settings.has_auth)

        # zotero_list_id should have no effect
        self.node_settings.zotero_list_id = 'totally fake ID'
        assert_true(self.node_settings.has_auth)

    def test_selected_folder_name_root(self):
        self.node_settings.zotero_list_id = 'ROOT'

        assert_equal(
            self.node_settings.selected_folder_name,
            "All Documents"
        )

    def test_selected_folder_name_empty(self):
        self.node_settings.zotero_list_id = None

        assert_equal(
            self.node_settings.selected_folder_name,
            ''
        )

    @mock.patch('website.addons.zotero.model.Zotero._folder_metadata')
    def test_selected_folder_name(self, mock_folder_metadata):
        # Mock the return from api call to get the folder's name
        mock_folder = {'data': {'name': 'Fake Folder'}}

        # Add the mocked return object to the mocked api client
        mock_folder_metadata.return_value = mock_folder

        self.node_settings.zotero_list_id = 'fake-list-id'

        assert_equal(
            self.node_settings.selected_folder_name,
            'Fake Folder'
        )




class ZoteroUserSettingsTestCase(OsfTestCase):
    def test_get_connected_accounts(self):
        # Get all Zotero accounts for user
        user_accounts = [ZoteroAccountFactory(), ZoteroAccountFactory()]
        user = UserFactory(external_accounts=user_accounts)
        user_addon = ZoteroUserSettingsFactory(owner=user)
        assert_equal(user_addon._get_connected_accounts(), user_accounts)

    def test_to_json(self):
        # All values are passed to the user settings view
        user_accounts = [ZoteroAccountFactory(), ZoteroAccountFactory()]
        user = UserFactory(external_accounts=user_accounts)
        user_addon = ZoteroUserSettingsFactory(owner=user)
        res = user_addon.to_json(user)
        for account in user_accounts:
            assert_in(
                {
                    'id': account._id,
                    'provider_id': account.provider_id,
                    'display_name': account.display_name
                },
                res['accounts'],
            )

    def _prep_oauth_case(self):
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.external_account = ExternalAccountFactory()

        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_or_add_addon('zotero')

    def test_grant_oauth_access_no_metadata(self):
        self._prep_oauth_case()

        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
        )
        self.user_settings.save()

        assert_equal(
            self.user_settings.oauth_grants,
            {self.node._id: {self.external_account._id: {}}},
        )

    def test_grant_oauth_access_metadata(self):
        self._prep_oauth_case()

        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )
        self.user_settings.save()

        assert_equal(
            self.user_settings.oauth_grants,
            {
                self.node._id: {
                    self.external_account._id: {'folder': 'fake_folder_id'}
                },
            }
        )

    def test_verify_oauth_access_no_metadata(self):
        self._prep_oauth_case()

        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
        )
        self.user_settings.save()

        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account
            )
        )

        assert_false(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=ExternalAccountFactory()
            )
        )

    def test_verify_oauth_access_metadata(self):
        self._prep_oauth_case()

        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )
        self.user_settings.save()

        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'folder': 'fake_folder_id'}
            )
        )

        assert_false(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'folder': 'another_folder_id'}
            )
        )
