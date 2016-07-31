# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.addons.base.exceptions import AddonError
from website.addons.owncloud.model import OwnCloudUserSettings

class TestCore(OsfTestCase):

    def setUp(self):

        super(TestCore, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('owncloud')
        self.user.save()


    def test_get_addon_returns_owncloud_user_settings(self):
        result = self.user.get_addon('owncloud')
        assert_true(isinstance(result, OwnCloudUserSettings))
