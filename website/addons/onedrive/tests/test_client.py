# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.addons.onedrive.model import OnedriveUserSettings


class TestCore(OsfTestCase):

    def setUp(self):

        super(TestCore, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('onedrive')
        self.user.save()

        self.settings = self.user.get_addon('onedrive')
        self.settings.save()

    def test_get_addon_returns_onedrive_user_settings(self):
        result = self.user.get_addon('onedrive')
        assert_true(isinstance(result, OnedriveUserSettings))
