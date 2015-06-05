# -*- coding: utf-8 -*-
import time
from datetime import datetime
from nose.tools import *  # noqa (PEP8 asserts)

import mock
from dateutil import relativedelta

from framework.auth import Auth
from framework.exceptions import PermissionsError
from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory
from website.addons.base import exceptions

from website.addons.googledrive.client import GoogleAuthClient
from website.addons.googledrive.model import (
    GoogleDriveUserSettings,
    GoogleDriveNodeSettings,
    GoogleDriveGuidFile,
)
from website.addons.googledrive.tests.factories import (
    GoogleDriveNodeSettingsFactory,
    GoogleDriveUserSettingsFactory,
)
from website.addons.googledrive import model


class TestFileGuid(OsfTestCase):
    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('googledrive', auth=Auth(self.user))
        self.node_addon = self.project.get_addon('googledrive')

        self.node_addon.drive_folder_id = 'Lulz'
        self.node_addon.folder_path = 'baz'
        self.node_addon.save()

    def test_path_doesnt_crash_without_addon(self):
        guid = GoogleDriveGuidFile(node=self.project, path='/baz/foo/bar')
        self.project.delete_addon('googledrive', Auth(self.user))

        assert_is(self.project.get_addon('googledrive'), None)

        assert_true(guid.path)
        assert_true(guid.waterbutler_path)

    def test_path_doesnt_crash_nonconfig_addon(self):
        guid = GoogleDriveGuidFile(node=self.project, path='/baz/foo/bar')
        self.node_addon.drive_folder_id = None
        self.node_addon.folder_path = '/'
        self.node_addon.save()
        self.node_addon.reload()

        assert_true(guid.path)
        assert_true(guid.waterbutler_path)

    def test_provider(self):
        assert_equal('googledrive', GoogleDriveGuidFile().provider)

    def test_correct_path(self):
        guid = GoogleDriveGuidFile(node=self.project, path='/baz/foo/bar')

        assert_equals(guid.path, '/baz/foo/bar')
        assert_equals(guid.waterbutler_path, '/foo/bar')

    @mock.patch('website.addons.base.requests.get')
    def test_unique_identifier(self, mock_get):
        mock_response = mock.Mock(ok=True, status_code=200)
        mock_get.return_value = mock_response
        mock_response.json.return_value = {
            'data': {
                'name': 'Morty',
                'extra': {
                    'revisionId': 'Ricksy'
                }
            }
        }

        guid = GoogleDriveGuidFile(node=self.project, path='/foo/bar')

        guid.enrich()
        assert_equals('Ricksy', guid.unique_identifier)

    def test_node_addon_get_or_create(self):
        guid, created = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created)
        assert_equal(guid.path, '/baz/foo/bar')
        assert_equal(guid.waterbutler_path, '/foo/bar')

    def test_node_addon_get_or_create_finds(self):
        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')
        guid2, created2 = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)

    def test_node_addon_get_or_create_finds_changed(self):
        self.node_addon.folder_path = 'baz'
        self.node_addon.save()
        self.node_addon.reload()

        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')

        self.node_addon.folder_path = 'baz/foo'
        self.node_addon.save()
        self.node_addon.reload()
        guid2, created2 = self.node_addon.find_or_create_file_guid('/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)

    def test_node_addon_get_or_create_finds_changed_root(self):
        self.node_addon.folder_path = 'baz'
        self.node_addon.save()
        self.node_addon.reload()

        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')

        self.node_addon.folder_path = '/'
        self.node_addon.save()
        self.node_addon.reload()
        guid2, created2 = self.node_addon.find_or_create_file_guid('/baz/foo/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)


class TestGoogleDriveProvider(OsfTestCase):
    def setUp(self):
        super(TestGoogleDriveProvider, self).setUp()
        self.provider = model.GoogleDriveProvider()

    @mock.patch.object(GoogleAuthClient, 'userinfo')
    def test_handle_callback(self, mock_client):
        fake_response = {'access_token': 'abc123'}
        fake_info = mock.Mock()
        fake_info = {'sub': '12345', 'name': 'fakename', 'profile': 'fakeUrl'}
        mock_client.return_value = fake_info
        res = self.provider.handle_callback(fake_response)
        assert_equal(res['provider_id'], '12345')
        assert_equal(res['display_name'], 'fakename')
        assert_equal(res['profile_url'], 'fakeUrl')


    @mock.patch.object(GoogleAuthClient, 'refresh')
    def test_refresh_token(self, mock_refresh):
        fake_access_token = 'abc123'
        fake_refresh_token = 'xyz456'
        mock_refresh.return_value = 'faketoken'

        res = self.provider._refresh_token(fake_access_token, fake_refresh_token)
        assert_equal(res, 'faketoken')


    @mock.patch.object(GoogleAuthClient, 'refresh')
    def test_refresh_token_without_refresh_token(self, mock_refresh):
        fake_access_token = 'abc123'
        fake_refresh_token = None
        mock_refresh.return_value = 'faketoken'

        res = self.provider._refresh_token(fake_access_token, fake_refresh_token)
        assert_false(res, 'faketoken')

class TestGoogleDriveUserSettings(OsfTestCase):

    def _prep_oauth_case(self):
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.external_account = ExternalAccountFactory()

        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_or_add_addon('googledrive')

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



class TestGoogleDriveNodeSettings(OsfTestCase):

    def setUp(self):
        super(TestGoogleDriveNodeSettings, self).setUp()
        self.node = ProjectFactory()
        self.node_settings = model.GoogleDriveNodeSettings(owner=self.node)
        self.node_settings.save()
        self.user = self.node.creator
        self.user_settings = self.user.get_or_add_addon('googledrive')

    def tearDown(self):
        super(TestGoogleDriveNodeSettings, self).tearDown()
        self.user_settings.remove()
        self.node_settings.remove()
        self.node.remove()
        self.user.remove()

    @mock.patch('website.addons.googledrive.model.GoogleDriveProvider')
    def test_api_not_cached(self, mock_gdp):
        # The first call to .api returns a new object
        api = self.node_settings.api
        mock_gdp.assert_called_once()
        assert_equal(api, mock_gdp())

    @mock.patch('website.addons.googledrive.model.GoogleDriveProvider')
    def test_api_cached(self, mock_gdp):
        # Repeated calls to .api returns the same object
        self.node_settings._api = 'testapi'
        api = self.node_settings.api
        assert_false(mock_gdp.called)
        assert_equal(api, 'testapi')

    def test_set_auth(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        # this should be reset after the call
        self.node_settings.drive_folder_id = 'anything'

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
            self.node_settings.drive_folder_id
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
        self.node_settings.drive_folder_id = 'something'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

        self.node_settings.clear_auth()

        assert_is_none(self.node_settings.external_account)
        assert_is_none(self.node_settings.drive_folder_id)
        assert_is_none(self.node_settings.user_settings)
        assert_is_none(self.node_settings.folder_path)
        assert_is_none(self.node_settings.drive_folder_name)

    def test_set_target_folder(self):

        folder = {
            'id': 'fake-folder-id',
            'name': 'fake-folder-name',
            'path': 'fake_path'
        }


        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        self.node_settings.set_auth(
            external_account=external_account,
            user=self.user,
            )

        assert_is_none(self.node_settings.drive_folder_id)

        self.node_settings.set_target_folder(
            folder,
            auth=Auth(user=self.user),
            )

        # instance was updated
        assert_equal(
            self.node_settings.drive_folder_id,
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

        log = self.node.logs[-1]
        assert_equal(log.action, 'googledrive_folder_selected')
        assert_equal(log.params['folder_id'], folder['id'])
        assert_equal(log.params['folder_name'], folder['name'])

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

        # mendeley_list_id should have no effect
        self.node_settings.drive_folder_id = None
        assert_true(self.node_settings.has_auth)

        # mendeley_list_id should have no effect
        self.node_settings.drive_folder_id = 'totally fake ID'
        assert_true(self.node_settings.has_auth)

    def test_selected_folder_name_root(self):
        self.node_settings.drive_folder_id = 'root'

        assert_equal(
            self.node_settings.selected_folder_name,
            "Full Google Drive"
        )

    def test_selected_folder_name_empty(self):
        self.node_settings.drive_folder_id = None

        assert_equal(
            self.node_settings.selected_folder_name,
            ''
        )

    def test_selected_folder_name(self):
        self.node_settings.drive_folder_id = 'fake-id'
        self.node_settings.drive_folder_name = 'fake-folder-name'
        self.node_settings.save()
        assert_equal(
            self.node_settings.selected_folder_name,
            'fake-folder-name'
        )

    def test_serialize_credentials(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.node_settings.set_auth(external_account, self.user)
        credentials = self.node_settings.serialize_waterbutler_credentials()
        expected = {'token': self.node_settings.fetch_access_token()}
        assert_equal(credentials, expected)

    def test_serialize_credentials_not_authorized(self):
        external_account = ExternalAccountFactory()
        self.node_settings.external_account = external_account
        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_credentials()

    def test_serialize_settings(self):
        self.node_settings.folder_path = 'camera uploads/pizza.nii'
        self.node_settings.drive_folder_id = 'fake-id'
        self.node_settings.drive_folder_name = 'fake-folder-name'
        self.node_settings.save()

        settings = self.node_settings.serialize_waterbutler_settings()

        expected = {
            'folder': {
                'id': 'fake-id',
                'name': 'fake-folder-name',
                'path': 'camera uploads/pizza.nii',
                }
        }

        assert_equal(settings, expected)

    def test_serialize_settings_not_configured(self):
        self.node_settings.folder_id = None
        self.node_settings.save()

        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_settings()
    #
    # def test_create_log(self):
    #     action = 'file_added'
    #     path = '12345/camera uploads/pizza.nii'
    #     self.project = ProjectFactory()
    #
    #     nlog = len(self.project.logs)
    #     self.node_settings.create_waterbutler_log(
    #      auth=Auth(user=self.user),
    #      action=action,
    #      metadata={'path': path},
    #     )
    #
    #     self.project.reload()
    #
    #     assert_equal(len(self.project.logs), nlog + 1)
    #     assert_equal(
    #      self.project.logs[-1].action,
    #      'googledrive_{0}'.format(action),
    #     )
    #     assert_equal(self.project.logs[-1].params['path'], path)

    def test_fetch_access_token_with_token_not_expired(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        external_account.expires_at = datetime.utcnow() + relativedelta.relativedelta(minutes=6)
        external_account.oauth_key = 'fake-token'
        external_account.save()
        self.node_settings.set_auth(external_account, self.user)
        assert_equal(self.node_settings.fetch_access_token(), 'fake-token')

    @mock.patch.object(GoogleAuthClient, 'refresh')
    def test_fetch_access_token_with_token_expired(self, mock_refresh):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        external_account.expires_at = datetime.utcnow() + relativedelta.relativedelta(minutes=4)
        external_account.oauth_key = 'fake-token'
        external_account.refresh_token = 'refresh-fake-token'
        external_account.save()

        fake_token = {
            'access_token': 'new-access-token',
            'refresh_token': 'new-refresh-token',
            'expires_at': 1234.5
        }
        mock_refresh.return_value = fake_token
        self.node_settings.set_auth(external_account, self.user)
        self.node_settings.fetch_access_token()
        mock_refresh.assert_called_once()
        assert_equal(external_account.oauth_key, 'new-access-token')
        assert_equal(external_account.refresh_token, 'new-refresh-token')
        assert_equal(external_account.expires_at, datetime.utcfromtimestamp(1234.5))
