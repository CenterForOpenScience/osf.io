# -*- coding: utf-8 -*-
import time
from datetime import datetime
from nose.tools import *  # noqa (PEP8 asserts)

import mock
from dateutil import relativedelta

from framework.auth import Auth
from framework.exceptions import PermissionsError
from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.base import exceptions

from website.addons.googledrive import model
from website.addons.googledrive.client import GoogleAuthClient
from website.addons.googledrive.tests.factories import GoogleDriveAccountFactory

class TestGoogleDriveProvider(OsfTestCase):
    def setUp(self):
        super(TestGoogleDriveProvider, self).setUp()
        self.provider = model.GoogleDriveProvider()

    @mock.patch.object(GoogleAuthClient, 'userinfo')
    def test_handle_callback(self, mock_client):
        fake_response = {'access_token': 'abc123'}
        fake_info = {'sub': '12345', 'name': 'fakename', 'profile': 'fakeUrl'}
        mock_client.return_value = fake_info
        res = self.provider.handle_callback(fake_response)
        assert_equal(res['provider_id'], '12345')
        assert_equal(res['display_name'], 'fakename')
        assert_equal(res['profile_url'], 'fakeUrl')

class TestGoogleDriveUserSettings(OsfTestCase):
    def setUp(self):
        super(TestGoogleDriveUserSettings, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.external_account = GoogleDriveAccountFactory()

        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_or_add_addon('googledrive')

    def tearDown(self):
        super(TestGoogleDriveUserSettings, self).tearDown()
        self.user_settings.remove()
        self.external_account.remove()
        self.node.remove()
        self.user.remove()

    def test_grant_oauth_access_no_metadata(self):
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
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
        )
        self.user_settings.save()

        account_has_access = self.user_settings.verify_oauth_access(
            node=self.node,
            external_account=self.external_account
        )

        factory_account_has_access = self.user_settings.verify_oauth_access(
            node=self.node,
            external_account=GoogleDriveAccountFactory()
        )

        assert_true(account_has_access)
        assert_false(factory_account_has_access)

    def test_verify_oauth_access_metadata(self):
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )
        self.user_settings.save()

        correct_meta_access = self.user_settings.verify_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )

        incorrect_meta_no_access = self.user_settings.verify_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'another_folder_id'}
        )

        assert_true(correct_meta_access)
        assert_false(incorrect_meta_no_access)


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
        external_account = GoogleDriveAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        # this should be reset after the call
        self.node_settings.folder_id = 'anything'

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
            self.node_settings.folder_id
        )

        set_auth_gives_access = self.user_settings.verify_oauth_access(
            node=self.node,
            external_account=external_account,
        )

        assert_true(set_auth_gives_access)

    def test_set_auth_wrong_user(self):
        external_account = GoogleDriveAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        with assert_raises(PermissionsError):
            self.node_settings.set_auth(
                external_account=external_account,
                user=UserFactory()
            )

    def test_clear_auth(self):
        self.node_settings.external_account = GoogleDriveAccountFactory()
        self.node_settings.folder_id = 'something'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

        self.node_settings.clear_auth()

        assert_is_none(self.node_settings.external_account)
        assert_is_none(self.node_settings.folder_id)
        assert_is_none(self.node_settings.user_settings)
        assert_is_none(self.node_settings.folder_path)
        assert_is_none(self.node_settings.folder_name)

    def test_set_target_folder(self):

        folder = {
            'id': 'fake-folder-id',
            'name': 'fake-folder-name',
            'path': 'fake_path'
        }


        external_account = GoogleDriveAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        self.node_settings.set_auth(
            external_account=external_account,
            user=self.user,
            )

        assert_is_none(self.node_settings.folder_id)

        self.node_settings.set_target_folder(
            folder,
            auth=Auth(user=self.user),
            )

        # instance was updated
        assert_equal(
            self.node_settings.folder_id,
            'fake-folder-id',
            )

        has_access = self.user_settings.verify_oauth_access(
            node=self.node,
            external_account=external_account,
            metadata={'folder': 'fake-folder-id'}
        )

        # user_settings was updated
        assert_true(has_access)

        log = self.node.logs[-1]
        assert_equal(log.action, 'googledrive_folder_selected')
        assert_equal(log.params['folder'], folder['path'])

    def test_has_auth_false(self):
        external_account = GoogleDriveAccountFactory()

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
        external_account = GoogleDriveAccountFactory()
        self.user.external_accounts.append(external_account)

        self.node_settings.set_auth(external_account, self.user)

        self.node_settings.folder_id = None
        assert_true(self.node_settings.has_auth)

        self.node_settings.folder_id = 'totally fake ID'
        assert_true(self.node_settings.has_auth)

    def test_selected_folder_name_root(self):
        self.node_settings.folder_id = 'root'

        assert_equal(
            self.node_settings.selected_folder_name,
            "Full Google Drive"
        )

    def test_selected_folder_name_empty(self):
        self.node_settings.folder_id = None

        assert_equal(
            self.node_settings.selected_folder_name,
            ''
        )

    def test_selected_folder_name(self):
        self.node_settings.folder_id = 'fake-id'
        self.node_settings.folder_path = 'fake-folder-name'
        self.node_settings.save()
        assert_equal(
            self.node_settings.selected_folder_name,
            'fake-folder-name'
        )

    @mock.patch('website.addons.googledrive.model.GoogleDriveProvider.refresh_oauth_key')
    def test_serialize_credentials(self, mock_refresh):
        mock_refresh.return_value = True
        external_account = GoogleDriveAccountFactory()
        self.user.external_accounts.append(external_account)
        self.node_settings.set_auth(external_account, self.user)
        credentials = self.node_settings.serialize_waterbutler_credentials()
        expected = {'token': self.node_settings.fetch_access_token()}
        assert_equal(credentials, expected)

    @mock.patch('website.addons.googledrive.model.GoogleDriveProvider.refresh_oauth_key')
    def test_serialize_credentials_not_authorized(self, mock_refresh):
        mock_refresh.return_value = True
        external_account = GoogleDriveAccountFactory()
        self.node_settings.external_account = external_account
        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_credentials()

    def test_serialize_settings(self):
        self.node_settings.folder_id = 'fake-id'
        self.node_settings.folder_path = 'fake-folder-name'
        self.node_settings.save()

        settings = self.node_settings.serialize_waterbutler_settings()

        expected = {
            'folder': {
                'id': 'fake-id',
                'name': 'fake-folder-name',
                'path': 'fake-folder-name',
                }
        }

        assert_equal(settings, expected)

    def test_serialize_settings_not_configured(self):
        self.node_settings.folder_id = None
        self.node_settings.save()

        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_settings()

    def test_fetch_access_token_with_token_not_expired(self):
        external_account = GoogleDriveAccountFactory()
        self.user.external_accounts.append(external_account)
        external_account.expires_at = datetime.utcnow() + relativedelta.relativedelta(minutes=6)
        external_account.oauth_key = 'fake-token'
        external_account.save()
        self.node_settings.set_auth(external_account, self.user)
        assert_equal(self.node_settings.fetch_access_token(), 'fake-token')
