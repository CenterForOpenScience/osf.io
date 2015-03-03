# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)
from dropbox.client import DropboxClient

from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.addons.base.exceptions import AddonError
from website.addons.dropbox.model import DropboxUserSettings
from website.addons.dropbox.tests.factories import (
    DropboxNodeSettingsFactory,
    DropboxUserSettingsFactory
)
from website.addons.dropbox.client import (
    get_client, get_node_addon_client, get_node_client,
    get_client_from_user_settings
)


class TestCore(OsfTestCase):

    def setUp(self):

        super(TestCore, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('dropbox')
        self.user.save()

        self.settings = self.user.get_addon('dropbox')
        self.settings.access_token = '12345'
        self.settings.save()

    def test_get_addon_returns_dropbox_user_settings(self):
        result = self.user.get_addon('dropbox')
        assert_true(isinstance(result, DropboxUserSettings))


class TestClientHelpers(OsfTestCase):

    def setUp(self):

        super(TestClientHelpers, self).setUp()

        self.user_settings = DropboxUserSettingsFactory()
        self.node_settings = DropboxNodeSettingsFactory(user_settings=self.user_settings)
        self.user = self.user_settings.owner
        self.node = self.node_settings.owner

    def test_get_client_returns_a_dropbox_client(self):
        client = get_client(self.user)
        assert_true(isinstance(client, DropboxClient))

    def test_get_client_raises_addon_error_if_user_doesnt_have_addon_enabled(self):
        user_no_dropbox = UserFactory()
        with assert_raises(AddonError):
            get_client(user_no_dropbox)

    def test_get_node_addon_client(self):
        client = get_node_addon_client(self.node_settings)
        assert_true(isinstance(client, DropboxClient))

    def test_get_node_client(self):
        client = get_node_client(self.node)
        assert_true(isinstance(client, DropboxClient))

    def test_get_client_from_user_settings(self):
        client = get_client_from_user_settings(self.user_settings)
        assert_true(isinstance(client, DropboxClient))
