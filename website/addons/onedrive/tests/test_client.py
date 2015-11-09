# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.addons.box.model import BoxUserSettings


class TestCore(OsfTestCase):

    def setUp(self):

        super(TestCore, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('box')
        self.user.save()

        self.settings = self.user.get_addon('box')
        self.settings.save()

    def test_get_addon_returns_box_user_settings(self):
        result = self.user.get_addon('box')
        assert_true(isinstance(result, BoxUserSettings))
