# -*- coding: utf-8 -*-
import mock
from nose.tools import *

from website.addons.dropbox.model import DropboxUserSettings, DropboxNodeSettings
from website.addons.dropbox.core import init_storage
from tests.base import DbTestCase, fake
from tests.factories import UserFactory

from website.addons.dropbox.tests.factories import (
    DropboxUserSettingsFactory, DropboxNodeSettingsFactory
)

init_storage()


class TestUserSettingsModel(DbTestCase):

    def setUp(self):
        self.user = UserFactory()

    def test_fields(self):
        user_settings = DropboxUserSettings(
            access_token='12345',
            dropbox_id='abc',
            account_info={
                'display_name': self.user.fullname,
                'email': self.user.username
            },
            owner=self.user)
        user_settings.save()
        retrieved = DropboxUserSettings.load(user_settings._primary_key)
        assert_true(retrieved.access_token)
        assert_true(retrieved.dropbox_id)
        assert_true(retrieved.owner)
        assert_true(retrieved.account_info)
        assert_equal(retrieved.account_info['display_name'], self.user.fullname)

    def test_get_account_info(self):
        mock_client = mock.Mock()
        name, email = fake.name(), fake.email()
        mock_client.account_info.return_value = {
            'display_name': name,
            'email': email,
            'uid': '12345abc'
        }
        settings = DropboxUserSettingsFactory()
        settings.get_account_info(client=mock_client)
        settings.save()
        acct_info = settings.account_info
        assert_equal(acct_info['display_name'], name)
        assert_equal(acct_info['email'], email)

    def test_has_auth(self):
        user_settings = DropboxUserSettingsFactory(access_token=None)
        assert_false(user_settings.has_auth)
        user_settings.access_token = '12345'
        user_settings.save()
        assert_true(user_settings.has_auth)

    def test_clear_auth(self):
        user_settings = DropboxUserSettingsFactory(access_token='abcde',
            dropbox_id='abc')

        assert_true(user_settings.access_token)
        user_settings.clear_auth()
        user_settings.save()
        assert_false(user_settings.access_token)
        assert_false(user_settings.dropbox_id)


    def test_delete(self):
        user_settings = DropboxUserSettingsFactory()
        assert_true(user_settings.has_auth)
        user_settings.delete()
        user_settings.save()
        assert_false(user_settings.access_token)
        assert_false(user_settings.dropbox_id)

    def test_to_json(self):
        user_settings = DropboxUserSettingsFactory()
        result = user_settings.to_json()
        assert_equal(result['has_auth'], user_settings.has_auth)

# TODO
class TestDropboxNodeSettingsModel(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.user.add_addon('dropbox')
        self.user.save()
        self.user_settings = self.user.get_addon('dropbox')

    def test_fields(self):
        node_settings = DropboxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_true(node_settings.user_settings)
        assert_equal(node_settings.user_settings.owner, self.user)
        assert_equal(node_settings.folder, '')  # Defaults to dropbox root

    def test_has_auth(self):
        settings = DropboxNodeSettings(user_settings=self.user_settings)
        settings.save()
        assert_false(settings.has_auth)

        settings.user_settings.access_token = '123abc'
        settings.user_settings.save()
        assert_true(settings.has_auth)

    def test_to_json(self):
        settings = DropboxNodeSettingsFactory(
            user_settings=self.user_settings
        )
        user = UserFactory()
        result = settings.to_json(user)
        assert_equal(result['addon_short_name'], 'dropbox')
        assert_equal(result['folder'], settings.folder)
        assert_equal(result['node_has_auth'], settings.has_auth)
        assert_equal(result['is_owner'], settings.user_settings.owner == user)
        assert_equal(result['owner_info'], settings.user_settings.account_info)
