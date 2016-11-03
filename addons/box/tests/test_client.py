# -*- coding: utf-8 -*-
from nose.tools import assert_true
import pytest
import unittest

from osf_tests.factories import UserFactory

from addons.box.models import UserSettings

pytestmark = pytest.mark.django_db

class TestCore(unittest.TestCase):

    def setUp(self):

        super(TestCore, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('box')
        self.user.save()

        self.settings = self.user.get_addon('box')
        self.settings.save()

    def test_get_addon_returns_box_user_settings(self):
        result = self.user.get_addon('box')
        assert_true(isinstance(result, UserSettings))
