# -*- coding: utf-8 -*-

from nose.tools import *

from website.addons.dropbox.model import DropboxUserSettings
from website.addons.dropbox.core import init_storage
from tests.base import DbTestCase
from tests.factories import UserFactory

from website.addons.dropbox.tests.factories import DropboxUserSettingsFactory

init_storage()


class TestUserSettingsModel(DbTestCase):

    def setUp(self):
        self.user = UserFactory()

    def test_fields(self):
        user_settings = DropboxUserSettings(
            access_token='12345',
            dropbox_id='abc',
            owner=self.user)
        user_settings.save()
        assert_true(user_settings.access_token)
        assert_true(user_settings.dropbox_id)
        assert_true(user_settings.owner)

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

# TODO
class TestDropboxNodeSettingsModel(DbTestCase):
    pass

